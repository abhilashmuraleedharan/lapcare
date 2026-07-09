# SPDX-License-Identifier: GPL-3.0-or-later
"""The diagnostics engine: pure checks + explainable aggregate score.

Each check is a pure function from Optional input data to a
DiagnosticResult; ``run()`` is the one orchestrator that gathers inputs
through ports (core Protocols — no I/O of its own) with per-source
degradation: a source that cannot answer makes its check SKIPPED with a
skip_code, never an exception to the caller.

Privilege rule (ADR-0004/ADR-0006): ``run()`` touches the privileged SMART
path only when ``include_storage_health=True`` — callers pass True only from
a visually privilege-marked action. A declined prompt degrades to
SKIPPED("declined") and every other check still runs.

The score is deliberately transparent (constitution: every assessment must
be explainable): OK = 1, WARNING = 0.5, CRITICAL = 0, averaged over the
measured (non-SKIPPED) checks, as a 0-100 integer. SKIPPED checks reduce
coverage (measured/total), never the score itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lapcare.core.battery_analysis import HealthClass, classify_wear, wear_percent
from lapcare.core.errors import LapcareError, PrivilegedActionDenied, ProviderUnavailable
from lapcare.core.models import (
    BatteryWear,
    CheckStatus,
    Confidence,
    DiagnosticResult,
    DiagnosticsReport,
    DiskUsage,
    FirmwareRelease,
    SmartReport,
    TemperatureReading,
)

if TYPE_CHECKING:
    from lapcare.core.ports import (
        BatteryWearProvider,
        DiskUsageProvider,
        FirmwareProvider,
        StorageProvider,
        ThermalProvider,
    )

CHECK_IDS = ("battery-wear", "storage-health", "firmware-currency", "thermal", "disk-space")

# Thermal sanity bounds. Below PLAUSIBLE_MIN or above PLAUSIBLE_MAX is a
# sensor artifact, not a reading (E16 EC: unpopulated slots read 2 °C).
PLAUSIBLE_MIN_C = 1.0
PLAUSIBLE_MAX_C = 119.0
THERMAL_WARN_C = 85.0
THERMAL_CRIT_C = 95.0

DISK_WARN_FREE_PCT = 10.0
DISK_CRIT_FREE_PCT = 5.0

# NVMe wear: percentage_used is the drive's own rated-endurance estimate.
ENDURANCE_WARN_PCT = 80


def _skipped(check_id: str, skip_code: str) -> DiagnosticResult:
    return DiagnosticResult(
        check_id=check_id,
        status=CheckStatus.SKIPPED,
        confidence=Confidence.LOW,
        skip_code=skip_code,
    )


def check_battery_wear(wears: list[BatteryWear] | None) -> DiagnosticResult:
    if wears is None:
        return _skipped("battery-wear", "unavailable")
    if not wears:
        return _skipped("battery-wear", "no-data")  # a desktop: nothing to assess
    worst: float | None = None
    for battery in wears:
        wear = wear_percent(battery.capacity_full, battery.capacity_design)
        if wear is not None and (worst is None or wear > worst):
            worst = wear
    if worst is None:
        # Battery present but capacities unreadable: measured nothing.
        return _skipped("battery-wear", "no-data")
    health = classify_wear(worst)
    status = {
        HealthClass.GOOD: CheckStatus.OK,
        HealthClass.FAIR: CheckStatus.WARNING,
        HealthClass.POOR: CheckStatus.CRITICAL,
    }.get(health, CheckStatus.SKIPPED)
    return DiagnosticResult(
        check_id="battery-wear",
        status=status,
        confidence=Confidence.HIGH,
        metrics=(("wear_pct", f"{worst:.1f}"), ("batteries", str(len(wears)))),
    )


def check_storage_health(reports: list[SmartReport] | None, skip_code: str) -> DiagnosticResult:
    if reports is None:
        return _skipped("storage-health", skip_code)
    if not reports:
        return _skipped("storage-health", "no-data")
    metrics: list[tuple[str, str]] = []
    status = CheckStatus.OK
    confidence = Confidence.HIGH
    for report in reports:
        if report.passed is False:
            status = CheckStatus.CRITICAL
            metrics.append(("failing_device", report.device_name))
        elif report.passed is None:
            confidence = Confidence.MEDIUM  # drive did not report a verdict
        if report.pending_sectors and status is CheckStatus.OK:
            status = CheckStatus.WARNING
            metrics.append(("pending_sectors", str(report.pending_sectors)))
        if (
            report.percentage_used is not None
            and report.percentage_used >= ENDURANCE_WARN_PCT
            and status is CheckStatus.OK
        ):
            status = CheckStatus.WARNING
            metrics.append(("endurance_used_pct", str(report.percentage_used)))
    metrics.append(("devices", str(len(reports))))
    return DiagnosticResult(
        check_id="storage-health",
        status=status,
        confidence=confidence,
        metrics=tuple(metrics),
    )


def check_firmware_currency(pending: list[FirmwareRelease] | None) -> DiagnosticResult:
    if pending is None:
        return _skipped("firmware-currency", "unavailable")
    if not pending:
        return DiagnosticResult(
            check_id="firmware-currency",
            status=CheckStatus.OK,
            confidence=Confidence.MEDIUM,  # only as current as the last metadata refresh
        )
    critical = any(release.urgency == "critical" for release in pending)
    return DiagnosticResult(
        check_id="firmware-currency",
        status=CheckStatus.CRITICAL if critical else CheckStatus.WARNING,
        confidence=Confidence.MEDIUM,
        metrics=(("pending_updates", str(len(pending))),),
    )


def check_thermal(temps: list[TemperatureReading] | None) -> DiagnosticResult:
    if temps is None:
        return _skipped("thermal", "unavailable")
    plausible = [t for t in temps if PLAUSIBLE_MIN_C < t.celsius < PLAUSIBLE_MAX_C]
    if not plausible:
        return _skipped("thermal", "no-data")
    hottest = max(plausible, key=lambda t: t.celsius)
    if hottest.celsius >= THERMAL_CRIT_C:
        status = CheckStatus.CRITICAL
    elif hottest.celsius >= THERMAL_WARN_C:
        status = CheckStatus.WARNING
    else:
        status = CheckStatus.OK
    return DiagnosticResult(
        check_id="thermal",
        status=status,
        confidence=Confidence.MEDIUM,  # hwmon coverage varies by model
        metrics=(
            ("max_temp_c", f"{hottest.celsius:.0f}"),
            ("max_temp_source", hottest.label or hottest.chip),
            ("sensors", str(len(plausible))),
        ),
    )


def check_disk_space(usages: list[DiskUsage] | None) -> DiagnosticResult:
    if usages is None:
        return _skipped("disk-space", "unavailable")
    if not usages:
        return _skipped("disk-space", "no-data")
    status = CheckStatus.OK
    metrics: list[tuple[str, str]] = []
    fullest: tuple[float, str] | None = None
    for usage in usages:
        if usage.total_bytes <= 0:
            continue
        free_pct = usage.free_bytes / usage.total_bytes * 100.0
        if fullest is None or free_pct < fullest[0]:
            fullest = (free_pct, usage.mountpoint)
        if free_pct < DISK_CRIT_FREE_PCT:
            status = CheckStatus.CRITICAL
            metrics.append(("critical_mount", usage.mountpoint))
        elif free_pct < DISK_WARN_FREE_PCT and status is CheckStatus.OK:
            status = CheckStatus.WARNING
            metrics.append(("low_mount", usage.mountpoint))
    if fullest is None:
        return _skipped("disk-space", "no-data")
    metrics.append(("min_free_pct", f"{fullest[0]:.1f}"))
    metrics.append(("min_free_mount", fullest[1]))
    return DiagnosticResult(
        check_id="disk-space",
        status=status,
        confidence=Confidence.HIGH,
        metrics=tuple(metrics),
    )


def score(results: tuple[DiagnosticResult, ...]) -> tuple[int | None, int, int]:
    """(score 0-100 or None, measured, total) — the transparent aggregate."""
    points = {CheckStatus.OK: 1.0, CheckStatus.WARNING: 0.5, CheckStatus.CRITICAL: 0.0}
    measured = [r for r in results if r.status is not CheckStatus.SKIPPED]
    if not measured:
        return None, 0, len(results)
    value = round(100.0 * sum(points[r.status] for r in measured) / len(measured))
    return value, len(measured), len(results)


async def run(
    *,
    battery_wear: BatteryWearProvider | None,
    storage: StorageProvider | None,
    firmware: FirmwareProvider | None,
    thermal: ThermalProvider | None,
    disk: DiskUsageProvider | None,
    include_storage_health: bool = False,
) -> DiagnosticsReport:
    """Gather every input with per-source degradation, then run the checks."""
    wears: list[BatteryWear] | None = None
    if battery_wear is not None:
        try:
            wears = await battery_wear.list_batteries()
        except LapcareError:
            wears = None

    reports: list[SmartReport] | None = None
    storage_skip = "not-requested"
    if include_storage_health and storage is not None:
        try:
            reports = []
            for disk_device in await storage.list_devices():
                reports.append(await storage.read_smart(disk_device.name))
        except PrivilegedActionDenied:
            reports = None
            storage_skip = "declined"
        except ProviderUnavailable:
            reports = None
            storage_skip = "unavailable"
        except LapcareError:
            reports = None
            storage_skip = "unavailable"

    pending: list[FirmwareRelease] | None = None
    if firmware is not None:
        try:
            pending = []
            for fw_device in await firmware.list_devices():
                if fw_device.updatable:
                    pending.extend(await firmware.list_upgrades(fw_device.id))
        except LapcareError:
            pending = None

    temps: list[TemperatureReading] | None = None
    if thermal is not None:
        try:
            temps = await thermal.list_temperatures()
        except LapcareError:
            temps = None

    usages: list[DiskUsage] | None = None
    if disk is not None:
        try:
            usages = await disk.list_usage()
        except LapcareError:
            usages = None

    results = (
        check_battery_wear(wears),
        check_storage_health(reports, storage_skip),
        check_firmware_currency(pending),
        check_thermal(temps),
        check_disk_space(usages),
    )
    value, measured, total = score(results)
    return DiagnosticsReport(results=results, score=value, measured=measured, total=total)
