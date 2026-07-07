# SPDX-License-Identifier: GPL-3.0-or-later
"""Hardware view-model: full identity + CPU/memory + device inventory."""

from __future__ import annotations

import logging
from gettext import gettext as _
from typing import TYPE_CHECKING

from gi.repository import GObject

from lapcare.core.errors import LapcareError, ProviderUnavailable
from lapcare.core.models import (
    Availability,
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
        # Read by the view on ready; plain attributes, not GObject properties.
        self.pci_devices: list[PciDevice] = []
        self.usb_devices: list[UsbDevice] = []
        # Per-inventory degradation notes ("" = inventory is fine). The page
        # stays READY when an inventory fails — graceful degradation is
        # per-panel here, whole-page only for identity (the page's core).
        self.pci_note = ""
        self.usb_note = ""

    def load(self) -> None:
        self.show_loading()
        self._scheduler.submit(self._gather(), self._apply, self.handle_error)

    def _inventory_note(self, exc: LapcareError) -> str:
        if isinstance(exc, ProviderUnavailable):
            if exc.reason is Availability.TOOL_MISSING and exc.tool:
                return _("Not available — install the '%s' package.") % exc.tool
            return _("Not available on this system.")
        return _("Could not be read.")

    async def _gather(
        self,
    ) -> tuple[
        SystemIdentity,
        CpuMemSummary,
        tuple[list[PciDevice], str],
        tuple[list[UsbDevice], str],
    ]:
        identity = await self._identity.read_identity()
        cpu_mem = await self._os_info.read_cpu_mem()

        pci: tuple[list[PciDevice], str]
        try:
            pci = (await self._inventory.list_pci(), "")
        except LapcareError as exc:
            # e.g. VMs without a PCI-visible chassis, or pciutils missing.
            log.debug("pci inventory degraded: %s", exc)
            pci = ([], self._inventory_note(exc))

        usb: tuple[list[UsbDevice], str]
        try:
            usb = (await self._inventory.list_usb(), "")
        except LapcareError as exc:
            # Real case: CI/cloud VMs have no USB subsystem; lsusb fails.
            log.debug("usb inventory degraded: %s", exc)
            usb = ([], self._inventory_note(exc))

        return identity, cpu_mem, pci, usb

    def _apply(
        self,
        data: tuple[
            SystemIdentity,
            CpuMemSummary,
            tuple[list[PciDevice], str],
            tuple[list[UsbDevice], str],
        ],
    ) -> None:
        identity, cpu_mem, (pci, pci_note), (usb, usb_note) = data
        self.pci_note = pci_note
        self.usb_note = usb_note

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
