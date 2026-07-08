# SPDX-License-Identifier: GPL-3.0-or-later
"""upower provider against python-dbusmock's UPower template.

dbusmock spawns a private system bus (DBUS_SYSTEM_BUS_ADDRESS), which
platform.dbus.system_bus() honors — the provider under test uses its real
code path end to end, including signal delivery.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys

import dbusmock
import pytest
from gi.repository import GLib

from lapcare.core.errors import ProviderUnavailable
from lapcare.core.models import Availability, BatteryState
from lapcare.providers.upower import UPowerDbus


class TestUPowerProvider(dbusmock.DBusTestCase):
    # The private system bus is session-shared (tests/providers/conftest.py);
    # the inherited tearDownClass would stop it for every later test class.
    @classmethod
    def setUpClass(cls) -> None:
        cls.dbus_con = cls.get_dbus(system_bus=True)

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def setUp(self) -> None:
        self.p_mock, self.obj_upower = self.spawn_server_template(
            "upower", {"OnBattery": False}, stdout=subprocess.PIPE
        )

    def tearDown(self) -> None:
        assert self.p_mock.stdout is not None
        self.p_mock.stdout.close()
        self.p_mock.terminate()
        self.p_mock.wait()

    def test_availability_ok(self) -> None:
        assert UPowerDbus().availability() is Availability.OK

    def test_no_batteries_is_empty_list(self) -> None:
        assert asyncio.run(UPowerDbus().read_status()) == []

    def test_charging_battery(self) -> None:
        self.obj_upower.AddChargingBattery("mock_BAT0", "Mock Battery", 30.0, 1200)
        (bat,) = asyncio.run(UPowerDbus().read_status())
        assert bat.state is BatteryState.CHARGING
        assert bat.percentage == 30.0
        assert bat.time_to_full_s == 1200
        assert bat.time_to_empty_s is None  # template reports 0 -> None

    def test_discharging_battery(self) -> None:
        self.obj_upower.AddDischargingBattery("mock_BAT0", "Mock Battery", 77.0, 90)
        (bat,) = asyncio.run(UPowerDbus().read_status())
        assert bat.state is BatteryState.DISCHARGING
        assert bat.percentage == 77.0
        assert bat.time_to_empty_s == 90

    def test_change_signal_reaches_callback(self) -> None:
        provider = UPowerDbus()
        fired: list[bool] = []
        provider.subscribe(lambda: fired.append(True))

        self.obj_upower.AddDischargingBattery("mock_BAT0", "Mock Battery", 50.0, 600)

        # Pump the default main context (signal delivery) with a deadline.
        deadline = GLib.get_monotonic_time() + 5_000_000
        context = GLib.MainContext.default()
        while not fired and GLib.get_monotonic_time() < deadline:
            context.iteration(False)
        assert fired, "UPower change signal never reached the callback"


@pytest.mark.skipif(sys.platform != "linux", reason="linux-only semantics")
def test_unreachable_bus_is_tool_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    # Point the provider at a dead socket: TOOL_MISSING, and read raises
    # ProviderUnavailable naming the upower package.
    def dead_bus():  # type: ignore[no-untyped-def]
        raise GLib.Error("no bus here")

    provider = UPowerDbus(bus_factory=dead_bus)
    assert provider.availability() is Availability.TOOL_MISSING
    with pytest.raises(ProviderUnavailable) as exc:
        asyncio.run(provider.read_status())
    assert exc.value.tool == "upower"
