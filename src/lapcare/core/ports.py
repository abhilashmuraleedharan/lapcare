# SPDX-License-Identifier: GPL-3.0-or-later
"""Ports: the Protocol interfaces implemented by providers and platform.

The architectural boundary described in ARCHITECTURE.md: UI and core depend on
these; adapters implement them; only the composition root (app.py) sees
concrete classes. Stdlib imports only.

Conventions every port follows:
- ``availability()`` is cheap and synchronous (existence checks, no I/O beyond
  a stat) and reports what the provider can currently deliver.
- Read methods are ``async`` and raise only the ``core.errors`` hierarchy.
- Returned models come from ``core.models``; fields are Optional-by-default —
  a provider returns what it could read, never invents values.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any, Protocol, TypeVar

from lapcare.core.models import (
    Availability,
    BatteryStatus,
    BatteryWear,
    CpuMemSummary,
    FirmwareDevice,
    FirmwareRelease,
    OsInfo,
    PciDevice,
    SmartReport,
    StorageDevice,
    SystemIdentity,
    ThinkpadInfo,
    UsbDevice,
    WearSnapshot,
)

T = TypeVar("T")


class Scheduler(Protocol):
    """Async execution port (implemented by platform.scheduler per ADR-0007).

    View-models submit a coroutine and receive exactly one callback on the
    GTK main thread. Defined here (not in platform) because it is an
    interface the UI depends on — the dependency rule points inward.
    """

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def submit(
        self,
        coro: Coroutine[Any, Any, T],
        on_success: Callable[[T], None],
        on_error: Callable[[BaseException], None],
    ) -> None: ...


class SystemIdentityProvider(Protocol):
    """DMI identity (implemented by providers.dmi)."""

    def availability(self) -> Availability: ...

    async def read_identity(self) -> SystemIdentity: ...


class OsInfoProvider(Protocol):
    """OS release / kernel / uptime and CPU-memory summary (providers.os_info)."""

    def availability(self) -> Availability: ...

    async def read_os(self) -> OsInfo: ...

    async def read_cpu_mem(self) -> CpuMemSummary: ...


class ThinkpadProvider(Protocol):
    """ThinkPad detection (providers.thinkpad_acpi; detection only in M1)."""

    def availability(self) -> Availability: ...

    async def detect(self) -> ThinkpadInfo: ...


class DeviceInventoryProvider(Protocol):
    """PCI/USB inventory (providers.pci_usb)."""

    def availability(self) -> Availability: ...

    async def list_pci(self) -> list[PciDevice]: ...

    async def list_usb(self) -> list[UsbDevice]: ...


class BatteryWearProvider(Protocol):
    """Static/wear battery data (providers.battery_sysfs). Empty list = no
    batteries (a desktop) — data, not unavailability."""

    def availability(self) -> Availability: ...

    async def list_batteries(self) -> list[BatteryWear]: ...


class BatteryStatusProvider(Protocol):
    """Live battery status (providers.upower)."""

    def availability(self) -> Availability: ...

    async def read_status(self) -> list[BatteryStatus]: ...

    def subscribe(self, on_change: Callable[[], None]) -> None:
        """Invoke ``on_change`` on the GTK main thread when status changes."""
        ...


class FirmwareProvider(Protocol):
    """Firmware devices/releases/updates via fwupd (providers.fwupd, ADR-0009).

    ``install()`` blocks for the whole download+verify+flash flow (fwupd's own
    job, not ours) and reports progress through ``on_progress`` — called with
    (percentage 0-100 or None if unknown, human status text), always on the
    GTK main thread. Raises ``FirmwareInstallFailed`` on a fwupd-reported
    failure and ``PrivilegedActionDenied`` when polkit auth is declined —
    callers must not treat the latter as an error (ADR-0004).
    """

    def availability(self) -> Availability: ...

    async def list_devices(self) -> list[FirmwareDevice]: ...

    async def list_upgrades(self, device_id: str) -> list[FirmwareRelease]: ...

    async def refresh_metadata(self) -> None: ...

    def battery_precondition(self) -> tuple[int | None, int | None]:
        """Current (battery_level, threshold) as fwupd reports them — cheap,
        synchronous, for the UI to check before offering Install."""
        ...

    async def install(
        self,
        device_id: str,
        release_version: str,
        on_progress: Callable[[int | None, str], None],
    ) -> None: ...

    def subscribe(self, on_change: Callable[[], None]) -> None:
        """Invoke ``on_change`` on the GTK main thread on device/remote changes."""
        ...


class StorageProvider(Protocol):
    """Block-device inventory and SMART health (providers.storage_smart).

    ``list_devices()`` is unprivileged (/sys/block) and never prompts.
    ``read_smart()`` goes through the ADR-0006 pkexec helper: the FIRST call
    may raise a polkit auth prompt (``auth_admin_keep`` covers followers), so
    the UI must only call it from a visually privilege-marked action
    (ADR-0004). Raises ``PrivilegedActionDenied`` on declined auth — quiet
    degradation, never an error page.
    """

    def availability(self) -> Availability: ...

    async def list_devices(self) -> list[StorageDevice]: ...

    async def read_smart(self, device_name: str) -> SmartReport: ...


class HistoryStore(Protocol):
    """Wear history persistence (platform.history, SQLite).

    Methods are synchronous; call them from provider-I/O context (inside a
    coroutine submitted to the Scheduler), never directly on the GTK thread.
    """

    def record_wear(self, snapshot: WearSnapshot) -> None:
        """Insert or replace the snapshot for (day, battery) — idempotent."""
        ...

    def wear_history(self, battery_name: str, limit: int = 365) -> list[WearSnapshot]:
        """Snapshots for one battery, ascending by day, at most ``limit``."""
        ...
