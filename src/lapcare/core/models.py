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


@dataclass(frozen=True)
class ThinkpadInfo:
    """ThinkPad detection result (thinkpad_acpi provider, detection only in M1)."""

    is_thinkpad: bool
    dmi_vendor_lenovo: bool = False
    acpi_driver_loaded: bool = False
    model: str | None = None  # product_family when identifiable
