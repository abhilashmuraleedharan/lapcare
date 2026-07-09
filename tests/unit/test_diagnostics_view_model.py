# SPDX-License-Identifier: GPL-3.0-or-later
"""Diagnostics view-model: idle-ready page, run flow, prose mapping."""

from __future__ import annotations

from lapcare.core.errors import PrivilegedActionDenied
from lapcare.core.models import (
    Availability,
    BatteryWear,
    DiskUsage,
    FirmwareDevice,
    FirmwareRelease,
    SmartReport,
    StorageDevice,
    TemperatureReading,
)
from lapcare.ui.pages.diagnostics.view_model import DiagnosticsViewModel

from .test_dashboard_view_model import ImmediateScheduler


class FakeBatteryWear:
    def __init__(self, wears: list[BatteryWear]) -> None:
        self._wears = wears

    def availability(self) -> Availability:
        return Availability.OK

    async def list_batteries(self) -> list[BatteryWear]:
        return self._wears


class FakeStorage:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def availability(self) -> Availability:
        return Availability.OK

    async def list_devices(self) -> list[StorageDevice]:
        return [StorageDevice(name="nvme0n1")]

    async def read_smart(self, device_name: str) -> SmartReport:
        if self.error is not None:
            raise self.error
        return SmartReport(device_name=device_name, passed=True, percentage_used=2)


class FakeFirmware:
    def __init__(self, pending: list[FirmwareRelease]) -> None:
        self._pending = pending

    def availability(self) -> Availability:
        return Availability.OK

    async def list_devices(self) -> list[FirmwareDevice]:
        return [FirmwareDevice(id="a" * 40, updatable=True)]

    async def list_upgrades(self, device_id: str) -> list[FirmwareRelease]:
        return self._pending

    async def refresh_metadata(self) -> None: ...

    def battery_precondition(self) -> tuple[int | None, int | None]:
        return (None, None)

    async def install(self, device_id: str, version: str, on_progress: object) -> None: ...

    def subscribe(self, on_change: object) -> None: ...


class FakeThermal:
    def availability(self) -> Availability:
        return Availability.OK

    async def list_temperatures(self) -> list[TemperatureReading]:
        return [TemperatureReading("thinkpad", "CPU", 49.0)]


class FakeDisk:
    def availability(self) -> Availability:
        return Availability.OK

    async def list_usage(self) -> list[DiskUsage]:
        return [DiskUsage(mountpoint="/", total_bytes=1000, free_bytes=500)]


def _vm(
    storage_error: Exception | None = None,
    pending: list[FirmwareRelease] | None = None,
) -> DiagnosticsViewModel:
    return DiagnosticsViewModel(
        ImmediateScheduler(),
        battery_wear=FakeBatteryWear(
            [BatteryWear(name="BAT0", capacity_full=95, capacity_design=100)]
        ),
        storage=FakeStorage(error=storage_error),
        firmware=FakeFirmware(pending or []),
        thermal=FakeThermal(),
        disk=FakeDisk(),
    )


def test_page_opens_ready_with_no_results() -> None:
    vm = _vm()
    vm.load()
    assert vm.props.state == "ready"
    assert vm.cards == []
    assert vm.props.score_text == ""


def test_run_all_healthy_scores_100_and_names_signals() -> None:
    vm = _vm()
    vm.load()
    vm.run()
    assert vm.props.busy_text == ""
    assert vm.props.score_text == "100 / 100"
    assert "5 of 5" in vm.props.coverage_text
    assert "Experimental" in vm.props.coverage_text
    by_id = {c.check_id: c for c in vm.cards}
    assert by_id["battery-wear"].status_text == "OK"
    assert by_id["battery-wear"].subtitle == "high confidence"
    assert ("Worst battery wear", "5.0%") in by_id["battery-wear"].evidence
    assert ("Hottest sensor", "49 °C") in by_id["thermal"].evidence


def test_run_declined_auth_marks_storage_not_measured() -> None:
    vm = _vm(storage_error=PrivilegedActionDenied("smart-report"))
    vm.load()
    vm.run()
    assert vm.props.state == "ready"  # never an error page (ADR-0004)
    assert "4 of 5" in vm.props.coverage_text
    storage = next(c for c in vm.cards if c.check_id == "storage-health")
    assert storage.status_text == "Not measured"
    assert "declined" in storage.subtitle


def test_run_pending_firmware_warns() -> None:
    vm = _vm(pending=[FirmwareRelease(version="1.1")])
    vm.load()
    vm.run()
    firmware = next(c for c in vm.cards if c.check_id == "firmware-currency")
    assert firmware.status_text == "Warning"
    assert vm.props.score_text != "100 / 100"
