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
    CpuMemSummary,
    OsInfo,
    PciDevice,
    SystemIdentity,
    ThinkpadInfo,
    UsbDevice,
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
