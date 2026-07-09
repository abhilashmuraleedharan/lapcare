# SPDX-License-Identifier: GPL-3.0-or-later
"""Diagnostics engine: every check's verdict logic, the transparent score,
and run()'s per-source degradation (including the privilege rule)."""

from __future__ import annotations

from lapcare.core import diagnostics
from lapcare.core.errors import PrivilegedActionDenied, ProviderUnavailable
from lapcare.core.models import (
    Availability,
    BatteryWear,
    CheckStatus,
    Confidence,
    DiagnosticResult,
    DiskUsage,
    FirmwareDevice,
    FirmwareRelease,
    SmartReport,
    StorageDevice,
    TemperatureReading,
)

GOOD_BATTERY = BatteryWear(name="BAT0", capacity_full=95, capacity_design=100)
WORN_BATTERY = BatteryWear(name="BAT0", capacity_full=60, capacity_design=100)
HEALTHY_NVME = SmartReport(device_name="nvme0n1", passed=True, percentage_used=2)
T = TemperatureReading


# -- individual checks --------------------------------------------------------


def test_battery_wear_good() -> None:
    result = diagnostics.check_battery_wear([GOOD_BATTERY])
    assert result.status is CheckStatus.OK
    assert result.confidence is Confidence.HIGH
    assert ("wear_pct", "5.0") in result.metrics


def test_battery_wear_poor_is_critical() -> None:
    assert diagnostics.check_battery_wear([WORN_BATTERY]).status is CheckStatus.CRITICAL


def test_battery_wear_worst_of_multiple() -> None:
    result = diagnostics.check_battery_wear([GOOD_BATTERY, WORN_BATTERY])
    assert result.status is CheckStatus.CRITICAL  # dual-battery: worst counts


def test_battery_wear_no_battery_is_skipped() -> None:
    result = diagnostics.check_battery_wear([])
    assert result.status is CheckStatus.SKIPPED
    assert result.skip_code == "no-data"


def test_battery_wear_unreadable_capacities_is_skipped() -> None:
    result = diagnostics.check_battery_wear([BatteryWear(name="BAT0")])
    assert result.status is CheckStatus.SKIPPED


def test_storage_health_ok() -> None:
    result = diagnostics.check_storage_health([HEALTHY_NVME], "not-requested")
    assert result.status is CheckStatus.OK
    assert result.confidence is Confidence.HIGH


def test_storage_health_failing_disk_is_critical_and_named() -> None:
    failing = SmartReport(device_name="sda", passed=False)
    result = diagnostics.check_storage_health([HEALTHY_NVME, failing], "")
    assert result.status is CheckStatus.CRITICAL
    assert ("failing_device", "sda") in result.metrics


def test_storage_health_pending_sectors_warn() -> None:
    suspect = SmartReport(device_name="sda", passed=True, pending_sectors=8)
    assert diagnostics.check_storage_health([suspect], "").status is CheckStatus.WARNING


def test_storage_health_worn_endurance_warns() -> None:
    worn = SmartReport(device_name="nvme0n1", passed=True, percentage_used=85)
    assert diagnostics.check_storage_health([worn], "").status is CheckStatus.WARNING


def test_storage_health_no_verdict_lowers_confidence() -> None:
    quiet = SmartReport(device_name="sda", passed=None)
    result = diagnostics.check_storage_health([quiet], "")
    assert result.status is CheckStatus.OK
    assert result.confidence is Confidence.MEDIUM


def test_storage_health_not_collected_keeps_skip_code() -> None:
    result = diagnostics.check_storage_health(None, "declined")
    assert result.status is CheckStatus.SKIPPED
    assert result.skip_code == "declined"


def test_firmware_currency_up_to_date() -> None:
    assert diagnostics.check_firmware_currency([]).status is CheckStatus.OK


def test_firmware_currency_pending_warns() -> None:
    result = diagnostics.check_firmware_currency([FirmwareRelease(version="1.1")])
    assert result.status is CheckStatus.WARNING
    assert ("pending_updates", "1") in result.metrics


def test_firmware_currency_critical_urgency() -> None:
    releases = [FirmwareRelease(version="1.1", urgency="critical")]
    assert diagnostics.check_firmware_currency(releases).status is CheckStatus.CRITICAL


def test_thermal_ignores_bogus_ec_slots() -> None:
    # The measured E16 pattern: idle ~50 °C with 2 °C artifacts in EC slots.
    temps = [T("thinkpad", "CPU", 49.0), T("thinkpad", None, 2.0), T("thinkpad", None, 0.0)]
    result = diagnostics.check_thermal(temps)
    assert result.status is CheckStatus.OK
    assert ("max_temp_c", "49") in result.metrics
    assert ("max_temp_source", "CPU") in result.metrics


def test_thermal_hot_warns_and_critical() -> None:
    assert diagnostics.check_thermal([T("coretemp", None, 86.0)]).status is CheckStatus.WARNING
    assert diagnostics.check_thermal([T("coretemp", None, 96.0)]).status is CheckStatus.CRITICAL


def test_thermal_only_artifacts_is_skipped() -> None:
    assert diagnostics.check_thermal([T("x", None, 0.0)]).status is CheckStatus.SKIPPED


def test_disk_space_levels() -> None:
    def usage(free_pct: float) -> DiskUsage:
        return DiskUsage(mountpoint="/", total_bytes=1000, free_bytes=int(10 * free_pct))

    assert diagnostics.check_disk_space([usage(50)]).status is CheckStatus.OK
    assert diagnostics.check_disk_space([usage(8)]).status is CheckStatus.WARNING
    assert diagnostics.check_disk_space([usage(2)]).status is CheckStatus.CRITICAL


def test_disk_space_reports_fullest_mount() -> None:
    usages = [
        DiskUsage(mountpoint="/", total_bytes=1000, free_bytes=500),
        DiskUsage(mountpoint="/home", total_bytes=1000, free_bytes=200),
    ]
    result = diagnostics.check_disk_space(usages)
    assert ("min_free_pct", "20.0") in result.metrics
    assert ("min_free_mount", "/home") in result.metrics


# -- score --------------------------------------------------------------------


def _result(status: CheckStatus) -> DiagnosticResult:
    return DiagnosticResult(check_id="x", status=status, confidence=Confidence.HIGH)


def test_score_is_transparent_average() -> None:
    results = (
        _result(CheckStatus.OK),
        _result(CheckStatus.WARNING),
        _result(CheckStatus.CRITICAL),
        _result(CheckStatus.SKIPPED),
    )
    value, measured, total = diagnostics.score(results)
    assert value == 50  # (1 + 0.5 + 0) / 3
    assert measured == 3
    assert total == 4


def test_score_nothing_measured_is_none() -> None:
    value, measured, _total = diagnostics.score((_result(CheckStatus.SKIPPED),))
    assert value is None
    assert measured == 0


# -- run() orchestration --------------------------------------------------------


class FakeBattery:
    def __init__(self, wears: list[BatteryWear]) -> None:
        self._wears = wears

    def availability(self) -> Availability:
        return Availability.OK

    async def list_batteries(self) -> list[BatteryWear]:
        return self._wears


class FakeStorage:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.smart_calls: list[str] = []

    def availability(self) -> Availability:
        return Availability.OK

    async def list_devices(self) -> list[StorageDevice]:
        return [StorageDevice(name="nvme0n1")]

    async def read_smart(self, device_name: str) -> SmartReport:
        self.smart_calls.append(device_name)
        if self.error is not None:
            raise self.error
        return HEALTHY_NVME


class FakeFirmware:
    def availability(self) -> Availability:
        return Availability.OK

    async def list_devices(self) -> list[FirmwareDevice]:
        return [FirmwareDevice(id="a" * 40, updatable=True)]

    async def list_upgrades(self, device_id: str) -> list[FirmwareRelease]:
        return []

    async def refresh_metadata(self) -> None: ...

    def battery_precondition(self) -> tuple[int | None, int | None]:
        return (None, None)

    async def install(self, device_id: str, version: str, on_progress: object) -> None: ...

    def subscribe(self, on_change: object) -> None: ...


class FakeThermal:
    def availability(self) -> Availability:
        return Availability.OK

    async def list_temperatures(self) -> list[TemperatureReading]:
        return [T("thinkpad", "CPU", 49.0)]


class FakeDisk:
    def availability(self) -> Availability:
        return Availability.OK

    async def list_usage(self) -> list[DiskUsage]:
        return [DiskUsage(mountpoint="/", total_bytes=1000, free_bytes=500)]


async def test_run_all_healthy_without_storage() -> None:
    report = await diagnostics.run(
        battery_wear=FakeBattery([GOOD_BATTERY]),
        storage=FakeStorage(),
        firmware=FakeFirmware(),
        thermal=FakeThermal(),
        disk=FakeDisk(),
    )
    assert report.score == 100
    assert report.measured == 4 and report.total == 5
    by_id = {r.check_id: r for r in report.results}
    # Privilege rule: storage stays SKIPPED unless explicitly requested.
    assert by_id["storage-health"].status is CheckStatus.SKIPPED
    assert by_id["storage-health"].skip_code == "not-requested"


async def test_run_includes_storage_when_requested() -> None:
    storage = FakeStorage()
    report = await diagnostics.run(
        battery_wear=FakeBattery([GOOD_BATTERY]),
        storage=storage,
        firmware=FakeFirmware(),
        thermal=FakeThermal(),
        disk=FakeDisk(),
        include_storage_health=True,
    )
    assert storage.smart_calls == ["nvme0n1"]
    assert report.measured == 5
    assert report.score == 100


async def test_run_declined_auth_degrades_to_skip() -> None:
    storage = FakeStorage(error=PrivilegedActionDenied("smart-report"))
    report = await diagnostics.run(
        battery_wear=FakeBattery([GOOD_BATTERY]),
        storage=storage,
        firmware=FakeFirmware(),
        thermal=FakeThermal(),
        disk=FakeDisk(),
        include_storage_health=True,
    )
    by_id = {r.check_id: r for r in report.results}
    assert by_id["storage-health"].skip_code == "declined"
    assert report.score == 100  # every other check still measured


async def test_run_missing_helper_degrades_to_skip() -> None:
    storage = FakeStorage(
        error=ProviderUnavailable("storage_smart", Availability.TOOL_MISSING, tool="x")
    )
    report = await diagnostics.run(
        battery_wear=FakeBattery([]),
        storage=storage,
        firmware=FakeFirmware(),
        thermal=FakeThermal(),
        disk=FakeDisk(),
        include_storage_health=True,
    )
    by_id = {r.check_id: r for r in report.results}
    assert by_id["storage-health"].skip_code == "unavailable"


async def test_run_without_any_provider_is_all_skipped() -> None:
    report = await diagnostics.run(
        battery_wear=None, storage=None, firmware=None, thermal=None, disk=None
    )
    assert report.score is None
    assert report.measured == 0 and report.total == 5
