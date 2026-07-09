# SPDX-License-Identifier: GPL-3.0-or-later
"""Domain models: frozen dataclasses, fields Optional by default.

Every field is Optional unless the fixture corpus proves it universal
(constitution invariant / ARCHITECTURE.md). Absence of hardware is data
(None / empty list); *inability to ask* is ProviderUnavailable (errors.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Availability(Enum):
    """What a provider can currently deliver (the seed of ADR-0008)."""

    OK = "ok"
    TOOL_MISSING = "tool-missing"
    UNSUPPORTED_HARDWARE = "unsupported-hardware"
    PERMISSION_DENIED = "permission-denied"


@dataclass(frozen=True)
class SystemIdentity:
    """DMI identity (/sys/class/dmi/id). E16 Gen 2 example in provider doc."""

    vendor: str | None = None  # sys_vendor, e.g. "LENOVO"
    product_name: str | None = None  # machine type model, e.g. "21MBCTO1WW"
    product_family: str | None = None  # e.g. "ThinkPad E16 Gen 2"
    product_version: str | None = None  # usually mirrors family on ThinkPads
    board_name: str | None = None
    bios_version: str | None = None  # e.g. "R2JET48W(1.25 )" — trailing space is real
    bios_date: str | None = None  # MM/DD/YYYY as DMI reports it
    serial: str | None = None  # root-only on most systems; None unprivileged


@dataclass(frozen=True)
class OsInfo:
    distro_name: str | None = None  # os-release PRETTY_NAME
    distro_version: str | None = None  # os-release VERSION_ID
    kernel: str | None = None  # /proc/sys/kernel/osrelease
    hostname: str | None = None
    uptime_seconds: float | None = None


@dataclass(frozen=True)
class CpuMemSummary:
    cpu_model: str | None = None  # cpuinfo "model name" (first entry)
    cpu_count: int | None = None  # logical CPUs (cpuinfo processor entries)
    memory_total_kib: int | None = None  # meminfo MemTotal


@dataclass(frozen=True)
class PciDevice:
    slot: str  # e.g. "00:02.0"
    device_class: str | None = None  # e.g. "VGA compatible controller"
    vendor: str | None = None
    device: str | None = None


@dataclass(frozen=True)
class UsbDevice:
    bus: str  # e.g. "001"
    device: str | None = None  # device number on the bus
    vendor_id: str | None = None  # e.g. "8087"
    product_id: str | None = None
    name: str | None = None  # human-readable "vendor product" text


class CapacityUnit(Enum):
    """Which sysfs unit family a battery reports (drivers vary — the E16
    Gen 2 reports energy_*; some ThinkPads/vendors report charge_*)."""

    MICRO_WATT_HOURS = "µWh"  # energy_full / energy_full_design
    MICRO_AMP_HOURS = "µAh"  # charge_full / charge_full_design


class BatteryState(Enum):
    UNKNOWN = "unknown"
    CHARGING = "charging"
    DISCHARGING = "discharging"
    NOT_CHARGING = "not-charging"  # threshold-managed ThinkPads report this on AC
    FULL = "full"
    EMPTY = "empty"


@dataclass(frozen=True)
class BatteryWear:
    """Static/wear data for one battery (battery_sysfs provider)."""

    name: str  # e.g. "BAT0"
    capacity_full: int | None = None  # last full capacity, in capacity_unit
    capacity_design: int | None = None  # design capacity, in capacity_unit
    capacity_unit: CapacityUnit | None = None
    cycle_count: int | None = None  # None when absent OR driver reports <= 0
    model_name: str | None = None
    manufacturer: str | None = None
    technology: str | None = None


@dataclass(frozen=True)
class BatteryStatus:
    """Live status for one battery (upower provider)."""

    name: str
    state: BatteryState = BatteryState.UNKNOWN
    percentage: float | None = None
    time_to_empty_s: int | None = None  # None when unknown (UPower reports 0)
    time_to_full_s: int | None = None
    energy_rate_w: float | None = None


@dataclass(frozen=True)
class WearSnapshot:
    """One battery's wear on one day — the unit of history (HistoryStore)."""

    day: str  # ISO date "YYYY-MM-DD"
    battery_name: str
    wear_percent: float | None = None
    cycle_count: int | None = None
    capacity_full: int | None = None
    capacity_design: int | None = None


@dataclass(frozen=True)
class ThinkpadInfo:
    """ThinkPad detection result (thinkpad_acpi provider, detection only in M1)."""

    is_thinkpad: bool
    dmi_vendor_lenovo: bool = False
    acpi_driver_loaded: bool = False
    model: str | None = None  # product_family when identifiable


class UpdateState(Enum):
    """Fwupd.UpdateState, narrowed to what the UI distinguishes (fwupd provider)."""

    UNKNOWN = "unknown"
    PENDING = "pending"  # scheduled, needs reboot to apply (offline updates)
    SUCCESS = "success"
    FAILED = "failed"
    FAILED_TRANSIENT = "failed-transient"  # retry may succeed (e.g. lost connection)
    NEEDS_REBOOT = "needs-reboot"


@dataclass(frozen=True)
class FirmwareDevice:
    """One device fwupd knows about (fwupd provider)."""

    id: str  # fwupd's internal device id — opaque, not a GUID we interpret
    name: str | None = None  # e.g. "ThinkPad E16 Gen 2 System Firmware"
    summary: str | None = None
    vendor: str | None = None
    version: str | None = None  # currently installed version
    version_lowest: str | None = None  # oldest version fwupd will allow flashing
    updatable: bool = False  # DeviceFlags.UPDATABLE
    needs_reboot: bool = False  # DeviceFlags.NEEDS_REBOOT (device, not update, flag)
    plugin: str | None = None  # e.g. "uefi_capsule", "thunderbolt" — which fwupd backend
    update_state: UpdateState = UpdateState.UNKNOWN
    update_error: str | None = None  # set when update_state is FAILED*


@dataclass(frozen=True)
class FirmwareRelease:
    """One available release for a device (fwupd provider). Identified by
    ``version`` within a device — the provider re-resolves the live
    ``Fwupd.Release`` object by (device_id, version) at install time rather
    than carrying it through the port boundary (ADR-0009)."""

    version: str
    name: str | None = None
    summary: str | None = None
    description: str | None = None  # release notes; AppStream markup, rendered as-is
    size: int | None = None  # bytes, when fwupd reports it
    urgency: str | None = None  # e.g. "critical", "high", "medium", "low"


@dataclass(frozen=True)
class StorageDevice:
    """One physical block device (storage_smart provider, unprivileged
    /sys/block inventory — entries without a device/ subdirectory are
    virtual: loop, zram, dm-*, and never listed)."""

    name: str  # kernel name, e.g. "nvme0n1" — the helper's argument (ADR-0006)
    model: str | None = None  # device/model; SATA pads to 16 chars, stripped
    size_bytes: int | None = None  # size (512-byte sectors) * 512
    removable: bool | None = None
    rotational: bool | None = None  # False for SSD/NVMe


@dataclass(frozen=True)
class SmartReport:
    """Parsed ``smartctl --json --all`` health for one device (storage_smart
    provider, via the ADR-0006 privileged helper). Fields absent from a
    drive's report are None — a partially-answering drive is data with gaps
    (e.g. the E16 Gen 2's NVMe lacks the optional self-test log)."""

    device_name: str
    passed: bool | None = None  # smart_status.passed; None if unreported
    temperature_c: int | None = None
    power_on_hours: int | None = None
    power_cycles: int | None = None
    # NVMe (nvme_smart_health_information_log)
    percentage_used: int | None = None  # wear estimate, 0-100+ (can exceed 100)
    available_spare_pct: int | None = None
    media_errors: int | None = None
    critical_warning: int | None = None  # NVMe bitmask; 0 = none
    unsafe_shutdowns: int | None = None
    # SATA (ata_smart_attributes ids 5 / 197)
    reallocated_sectors: int | None = None
    pending_sectors: int | None = None
    model: str | None = None
    firmware_version: str | None = None
    # Identifier (ADR-0006 §17): kept in its own field so redaction rules can
    # target it — never logged above DEBUG, excluded from exports by default.
    serial_number: str | None = None
    messages: tuple[str, ...] = ()  # smartctl error/warning strings (data quality)
