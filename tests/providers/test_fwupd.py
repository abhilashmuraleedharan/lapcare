# SPDX-License-Identifier: GPL-3.0-or-later
"""fwupd provider against the local dbusmock template (ADR-0009: no upstream
one exists). Covers the read-only surface end to end, real error-translation
paths that libfwupd raises without any network (no release URIs at all), and
network-touching failure paths against fast-failing unreachable addresses
(never real LVFS — see docs/status/m3-firmware-updates.md's deferral note).
A full successful install cannot be exercised here: it needs a real signed
.cab served over HTTPS and, for anything beyond ``list_devices``/
``list_upgrades``, an interactive polkit prompt (ADR-0004) — validated
manually on the E16 Gen 2.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

import dbus
import dbusmock
import pytest
from gi.repository import GLib

from lapcare.core.errors import (
    FirmwareInstallFailed,
    PrivilegedActionDenied,
    ProviderTimeout,
    ProviderUnavailable,
)
from lapcare.core.models import Availability, UpdateState
from lapcare.providers.fwupd import FwupdGir, _translate_install_error

TEMPLATE = str(Path(__file__).resolve().parents[1] / "dbusmock_templates" / "fwupd.py")
DEV_A = "a" * 40
DEV_B = "b" * 40


class TestFwupdProvider(dbusmock.DBusTestCase):
    # The private system bus is session-shared (tests/providers/conftest.py);
    # the inherited tearDownClass would stop it for every later test class.
    @classmethod
    def setUpClass(cls) -> None:
        cls.dbus_con = cls.get_dbus(system_bus=True)

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def setUp(self) -> None:
        self.p_mock, self.obj = self.spawn_server_template(TEMPLATE, {}, stdout=subprocess.PIPE)

    def tearDown(self) -> None:
        assert self.p_mock.stdout is not None
        self.p_mock.stdout.close()
        self.p_mock.terminate()
        self.p_mock.wait()

    def test_availability_ok(self) -> None:
        assert FwupdGir().availability() is Availability.OK

    def test_no_devices_is_empty_list(self) -> None:
        assert asyncio.run(FwupdGir().list_devices()) == []

    def test_device_mapping_and_sort_order(self) -> None:
        self.obj.AddDevice(
            DEV_B,
            dbus.Dictionary(
                {
                    "Name": dbus.String("ThinkPad EC"),
                    "Vendor": dbus.String("LENOVO"),
                    "Version": dbus.String("1.0"),
                    "Flags": dbus.UInt64(2),  # UPDATABLE
                    "UpdateState": dbus.UInt32(3),  # FAILED
                    "UpdateError": dbus.String("checksum mismatch"),
                },
                signature="sv",
            ),
        )
        self.obj.AddDevice(
            DEV_A,
            dbus.Dictionary({"Name": dbus.String("AMD Chipset")}, signature="sv"),
        )
        devices = asyncio.run(FwupdGir().list_devices())
        assert [d.name for d in devices] == ["AMD Chipset", "ThinkPad EC"]
        ec = devices[1]
        assert ec.id == DEV_B
        assert ec.vendor == "LENOVO"
        assert ec.updatable is True
        assert ec.needs_reboot is False
        assert ec.update_state is UpdateState.FAILED
        assert ec.update_error == "checksum mismatch"

    def test_upgrades_mapping(self) -> None:
        self.obj.AddDevice(DEV_A, dbus.Dictionary({"Name": dbus.String("EC")}, signature="sv"))
        self.obj.AddUpgrade(
            DEV_A,
            dbus.Dictionary(
                {
                    "Version": dbus.String("1.1"),
                    "Name": dbus.String("EC 1.1"),
                    "Summary": dbus.String("bugfixes"),
                    "Size": dbus.UInt64(2048),
                    "Urgency": dbus.UInt32(3),  # HIGH
                },
                signature="sv",
            ),
        )
        (release,) = asyncio.run(FwupdGir().list_upgrades(DEV_A))
        assert release.version == "1.1"
        assert release.size == 2048
        assert release.urgency == "high"

    def test_no_upgrades_is_empty_list(self) -> None:
        assert asyncio.run(FwupdGir().list_upgrades(DEV_A)) == []

    def test_nothing_to_do_error_is_empty_list(self) -> None:
        # Real fwupd raises rather than returning [] when it has nothing new.
        self.obj.AddMethod(
            "org.freedesktop.fwupd",
            "GetUpgrades",
            "s",
            "aa{sv}",
            'raise dbus.exceptions.DBusException("nothing", '
            'name="org.freedesktop.fwupd.NothingToDo")',
        )
        assert asyncio.run(FwupdGir().list_upgrades(DEV_A)) == []

    def test_refresh_metadata_no_enabled_remotes_is_noop(self) -> None:
        asyncio.run(FwupdGir().refresh_metadata())  # must not raise

    def test_refresh_metadata_ignores_local_remotes(self) -> None:
        self.obj.AddRemote(
            "local",
            dbus.Dictionary(
                {"Type": dbus.UInt32(2), "Flags": dbus.UInt64(1)},
                signature="sv",  # LOCAL, enabled
            ),
        )
        asyncio.run(FwupdGir().refresh_metadata())  # local remotes have no metadata to fetch

    def test_refresh_metadata_unreachable_remote_raises(self) -> None:
        self.obj.AddRemote(
            "lvfs",
            dbus.Dictionary(
                {
                    "Type": dbus.UInt32(1),  # DOWNLOAD
                    "Flags": dbus.UInt64(1),  # ENABLED
                    "Uri": dbus.String("http://127.0.0.1:1/firmware.xml.gz"),
                },
                signature="sv",
            ),
        )
        with pytest.raises(ProviderTimeout):
            asyncio.run(FwupdGir().refresh_metadata())

    def test_battery_precondition_unknown_sentinel_is_none(self) -> None:
        assert FwupdGir().battery_precondition() == (None, None)

    def test_battery_precondition_known_values(self) -> None:
        self.obj.Set("org.freedesktop.fwupd", "BatteryLevel", dbus.UInt32(42))
        self.obj.Set("org.freedesktop.fwupd", "BatteryThreshold", dbus.UInt32(30))
        assert FwupdGir().battery_precondition() == (42, 30)

    def test_install_release_no_longer_offered(self) -> None:
        self.obj.AddDevice(DEV_A, dbus.Dictionary({"Name": dbus.String("EC")}, signature="sv"))
        with pytest.raises(FirmwareInstallFailed) as exc:
            asyncio.run(FwupdGir().install(DEV_A, "9.9", lambda *_: None))
        assert exc.value.device_id == DEV_A

    def test_install_with_no_release_uris_fails_fast(self) -> None:
        # Real fwupd validates the release has a download location before
        # touching the network — deterministic, no LVFS/network involved.
        self.obj.AddDevice(DEV_A, dbus.Dictionary({"Name": dbus.String("EC")}, signature="sv"))
        self.obj.AddUpgrade(
            DEV_A,
            dbus.Dictionary(
                {"Version": dbus.String("1.1"), "Locations": dbus.Array([], signature="s")},
                signature="sv",
            ),
        )
        with pytest.raises(FirmwareInstallFailed):
            asyncio.run(FwupdGir().install(DEV_A, "1.1", lambda *_: None))

    def test_change_signal_reaches_callback(self) -> None:
        provider = FwupdGir()
        fired: list[bool] = []
        provider.subscribe(lambda: fired.append(True))

        self.obj.AddDevice(DEV_A, dbus.Dictionary({"Name": dbus.String("EC")}, signature="sv"))

        deadline = GLib.get_monotonic_time() + 5_000_000
        context = GLib.MainContext.default()
        while not fired and GLib.get_monotonic_time() < deadline:
            context.iteration(False)
        assert fired, "fwupd DeviceAdded signal never reached the callback"

    def test_progress_signal_reaches_on_progress(self) -> None:
        # subscribe() wires up the raw PropertiesChanged listener that
        # install() points at self._on_progress for the call's duration
        # (see providers/fwupd.py's module docstring for why not
        # Fwupd.Client's own notify signals). White-box: set the slot
        # directly rather than driving a real (untestable) install.
        provider = FwupdGir()
        provider.subscribe(lambda: None)
        seen: list[tuple[int | None, str]] = []
        provider._on_progress = lambda pct, status: seen.append((pct, status))

        self.obj.Set("org.freedesktop.fwupd", "Percentage", dbus.UInt32(55))
        self.obj.Set("org.freedesktop.fwupd", "Status", dbus.UInt32(8))  # DOWNLOADING

        deadline = GLib.get_monotonic_time() + 5_000_000
        context = GLib.MainContext.default()
        while not seen and GLib.get_monotonic_time() < deadline:
            context.iteration(False)
        assert seen, "fwupd PropertiesChanged never reached on_progress"


def test_translate_install_error_auth_denied() -> None:
    from gi.repository import Fwupd

    for code in (Fwupd.Error.AUTH_FAILED, Fwupd.Error.PERMISSION_DENIED):
        exc = GLib.Error.new_literal(Fwupd.error_quark(), "nope", code)
        translated = _translate_install_error("dev", exc)
        assert isinstance(translated, PrivilegedActionDenied)


def test_translate_install_error_other_is_install_failed() -> None:
    from gi.repository import Fwupd

    exc = GLib.Error.new_literal(Fwupd.error_quark(), "bad checksum", Fwupd.Error.INVALID_FILE)
    translated = _translate_install_error("dev", exc)
    assert isinstance(translated, FirmwareInstallFailed)
    assert translated.device_id == "dev"
    assert "bad checksum" in translated.detail


@pytest.mark.skipif(sys.platform != "linux", reason="linux-only semantics")
def test_availability_unreachable_bus_is_tool_missing() -> None:
    def dead_bus():  # type: ignore[no-untyped-def]
        raise GLib.Error("no bus here")

    assert FwupdGir(bus_factory=dead_bus).availability() is Availability.TOOL_MISSING


@pytest.mark.skipif(sys.platform != "linux", reason="linux-only semantics")
def test_list_devices_without_daemon_is_provider_unavailable() -> None:
    # Runs after the class's mocks are torn down: the session bus is up but
    # nothing owns org.freedesktop.fwupd, so Fwupd.Client's call fails with
    # ServiceUnknown — the containers/CI reality this provider degrades on.
    with pytest.raises(ProviderUnavailable) as exc:
        asyncio.run(FwupdGir().list_devices())
    assert exc.value.tool == "fwupd"
