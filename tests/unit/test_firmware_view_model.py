# SPDX-License-Identifier: GPL-3.0-or-later
"""Firmware view-model: states, degradation policy, and the update flow."""

from __future__ import annotations

from collections.abc import Callable

from lapcare.core.errors import (
    FirmwareInstallFailed,
    PrivilegedActionDenied,
    ProviderTimeout,
    ProviderUnavailable,
)
from lapcare.core.models import (
    Availability,
    FirmwareDevice,
    FirmwareRelease,
    UpdateState,
)
from lapcare.ui.pages.firmware.view_model import FirmwareViewModel

from .test_dashboard_view_model import ImmediateScheduler

DEV_EC = FirmwareDevice(
    id="a" * 40,
    name="ThinkPad EC",
    vendor="LENOVO",
    version="1.20",
    updatable=True,
    plugin="ec",
)
DEV_LOCKED = FirmwareDevice(id="b" * 40, name="UEFI dbx", version="371", updatable=False)
REL_121 = FirmwareRelease(
    version="1.21", name="EC Firmware", summary="Fixes fan control.", urgency="high"
)


class FakeFirmware:
    def __init__(
        self,
        devices: list[FirmwareDevice] | None = None,
        upgrades: dict[str, list[FirmwareRelease]] | None = None,
        battery: tuple[int | None, int | None] = (None, None),
    ) -> None:
        self.devices = devices
        self.upgrades = upgrades or {}
        self.battery = battery
        self.installs: list[tuple[str, str]] = []
        self.install_error: Exception | None = None
        self.refresh_error: Exception | None = None
        self.upgrade_error: Exception | None = None

    def availability(self) -> Availability:
        return Availability.OK if self.devices is not None else Availability.TOOL_MISSING

    async def list_devices(self) -> list[FirmwareDevice]:
        if self.devices is None:
            raise ProviderUnavailable("fwupd", Availability.TOOL_MISSING, tool="fwupd")
        return self.devices

    async def list_upgrades(self, device_id: str) -> list[FirmwareRelease]:
        if self.upgrade_error is not None:
            raise self.upgrade_error
        return self.upgrades.get(device_id, [])

    async def refresh_metadata(self) -> None:
        if self.refresh_error is not None:
            raise self.refresh_error

    def battery_precondition(self) -> tuple[int | None, int | None]:
        return self.battery

    async def install(
        self, device_id: str, version: str, on_progress: Callable[[int | None, str], None]
    ) -> None:
        if self.install_error is not None:
            raise self.install_error
        on_progress(50, "downloading")
        self.installs.append((device_id, version))

    def subscribe(self, on_change: Callable[[], None]) -> None:
        pass


def _vm(firmware: FakeFirmware) -> FirmwareViewModel:
    return FirmwareViewModel(ImmediateScheduler(), firmware=firmware)


def test_ready_with_upgrade_and_plain_device() -> None:
    vm = _vm(FakeFirmware([DEV_EC, DEV_LOCKED], {DEV_EC.id: [REL_121]}))
    vm.load()
    assert vm.props.state == "ready"
    ec, locked = vm.cards
    assert ec.title == "ThinkPad EC"
    assert ec.releases == [REL_121]
    assert not locked.updatable
    assert vm.props.reboot_banner == ""


def test_no_fwupd_daemon_is_unavailable_naming_the_package() -> None:
    vm = _vm(FakeFirmware(devices=None))
    vm.load()
    assert vm.props.state == "unavailable"
    assert "fwupd" in vm.props.unavailable_remedy


def test_zero_devices_is_unavailable_nothing_to_do() -> None:
    vm = _vm(FakeFirmware(devices=[]))
    vm.load()
    assert vm.props.state == "unavailable"
    assert "Nothing to do" in vm.props.unavailable_remedy


def test_one_device_upgrade_failure_degrades_to_note() -> None:
    fw = FakeFirmware([DEV_EC], {})
    fw.upgrade_error = ProviderTimeout("fwupd", "GetUpgrades stalled")
    vm = _vm(fw)
    vm.load()
    assert vm.props.state == "ready"  # the page survives
    (card,) = vm.cards
    assert card.upgrade_note != ""
    assert card.releases == []


def test_reboot_pending_device_raises_banner() -> None:
    pending = FirmwareDevice(
        id="c" * 40, name="System Firmware", update_state=UpdateState.NEEDS_REBOOT
    )
    vm = _vm(FakeFirmware([pending]))
    vm.load()
    assert vm.props.state == "ready"
    assert "System Firmware" in vm.props.reboot_banner
    assert "Restart" in vm.props.reboot_banner


def test_install_blocked_by_battery_precondition() -> None:
    fw = FakeFirmware([DEV_EC], {DEV_EC.id: [REL_121]}, battery=(15, 30))
    vm = _vm(fw)
    vm.load()
    vm.request_install(DEV_EC.id, REL_121)
    assert fw.installs == []  # never committed
    assert "15%" in vm.props.flow_banner and "30%" in vm.props.flow_banner


def test_install_success_reports_what_changed() -> None:
    fw = FakeFirmware([DEV_EC], {DEV_EC.id: [REL_121]})
    vm = _vm(fw)
    vm.load()
    vm.request_install(DEV_EC.id, REL_121)
    assert fw.installs == [(DEV_EC.id, "1.21")]
    assert vm.props.state == "ready"
    assert vm.props.busy_text == ""
    assert "1.21" in vm.props.result_text
    assert "Fixes fan control." in vm.props.result_text


def test_install_declined_auth_is_quiet_toast_not_error() -> None:
    fw = FakeFirmware([DEV_EC], {DEV_EC.id: [REL_121]})
    fw.install_error = PrivilegedActionDenied("org.freedesktop.fwupd.install")
    vm = _vm(fw)
    vm.load()
    vm.request_install(DEV_EC.id, REL_121)
    assert vm.props.state == "ready"  # never an error page (ADR-0004)
    assert vm.props.flow_banner == ""
    assert vm.props.toast_text != ""


def test_install_failure_is_retryable_banner_not_error_page() -> None:
    fw = FakeFirmware([DEV_EC], {DEV_EC.id: [REL_121]})
    fw.install_error = FirmwareInstallFailed(DEV_EC.id, "device rejected payload")
    vm = _vm(fw)
    vm.load()
    vm.request_install(DEV_EC.id, REL_121)
    assert vm.props.state == "ready"  # cards still there for the retry
    assert "device rejected payload" in vm.props.flow_banner
    assert "retry" in vm.props.flow_banner


def test_refresh_failure_is_toast_not_page_error() -> None:
    fw = FakeFirmware([DEV_EC], {DEV_EC.id: [REL_121]})
    fw.refresh_error = ProviderTimeout("fwupd", "all remotes unreachable: lvfs")
    vm = _vm(fw)
    vm.load()
    vm.refresh_metadata()
    assert vm.props.state == "ready"
    assert vm.props.busy_text == ""
    assert "refresh" in vm.props.toast_text.lower()
