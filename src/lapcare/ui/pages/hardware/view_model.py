# SPDX-License-Identifier: GPL-3.0-or-later
"""Hardware view-model: full identity + CPU/memory + device inventory."""

from __future__ import annotations

import logging
from gettext import gettext as _
from typing import TYPE_CHECKING

from gi.repository import GObject

from lapcare.core.models import (
    CpuMemSummary,
    PciDevice,
    SystemIdentity,
    UsbDevice,
)
from lapcare.ui.pages.base_view_model import PageViewModel

if TYPE_CHECKING:
    from lapcare.core.ports import (
        DeviceInventoryProvider,
        OsInfoProvider,
        Scheduler,
        SystemIdentityProvider,
    )

log = logging.getLogger(__name__)

PLACEHOLDER = "—"


def format_memory(kib: int | None) -> str:
    if kib is None:
        return PLACEHOLDER
    gib = kib / (1024 * 1024)
    return _("%.1f GiB") % gib


class HardwareViewModel(PageViewModel):
    __gtype_name__ = "LapcareHardwareViewModel"

    family = GObject.Property(type=str, default=PLACEHOLDER)
    machine_type = GObject.Property(type=str, default=PLACEHOLDER)
    board = GObject.Property(type=str, default=PLACEHOLDER)
    bios_version = GObject.Property(type=str, default=PLACEHOLDER)
    bios_date = GObject.Property(type=str, default=PLACEHOLDER)
    cpu_model = GObject.Property(type=str, default=PLACEHOLDER)
    cpu_count = GObject.Property(type=str, default=PLACEHOLDER)
    memory = GObject.Property(type=str, default=PLACEHOLDER)

    def __init__(
        self,
        scheduler: Scheduler,
        identity: SystemIdentityProvider,
        os_info: OsInfoProvider,
        inventory: DeviceInventoryProvider,
    ) -> None:
        super().__init__()
        self._scheduler = scheduler
        self._identity = identity
        self._os_info = os_info
        self._inventory = inventory
        # Read by the view on ready; plain lists, not GObject properties.
        self.pci_devices: list[PciDevice] = []
        self.usb_devices: list[UsbDevice] = []

    def load(self) -> None:
        self.show_loading()
        self._scheduler.submit(self._gather(), self._apply, self.handle_error)

    async def _gather(
        self,
    ) -> tuple[SystemIdentity, CpuMemSummary, list[PciDevice], list[UsbDevice]]:
        return (
            await self._identity.read_identity(),
            await self._os_info.read_cpu_mem(),
            await self._inventory.list_pci(),
            await self._inventory.list_usb(),
        )

    def _apply(
        self,
        data: tuple[SystemIdentity, CpuMemSummary, list[PciDevice], list[UsbDevice]],
    ) -> None:
        identity, cpu_mem, pci, usb = data

        self.props.family = identity.product_family or PLACEHOLDER
        self.props.machine_type = identity.product_name or PLACEHOLDER
        self.props.board = identity.board_name or PLACEHOLDER
        self.props.bios_version = identity.bios_version or PLACEHOLDER
        self.props.bios_date = identity.bios_date or PLACEHOLDER
        self.props.cpu_model = cpu_mem.cpu_model or PLACEHOLDER
        self.props.cpu_count = str(cpu_mem.cpu_count) if cpu_mem.cpu_count else PLACEHOLDER
        self.props.memory = format_memory(cpu_mem.memory_total_kib)
        self.pci_devices = pci
        self.usb_devices = usb

        log.debug("hardware ready pci=%d usb=%d", len(pci), len(usb))
        self.show_ready()
