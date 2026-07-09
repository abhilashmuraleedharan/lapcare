# SPDX-License-Identifier: GPL-3.0-or-later
"""Hardware view: identity/CPU/memory rows plus PCI/USB expander lists."""

import logging
from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from lapcare.ui.pages.hardware.view_model import HardwareViewModel

log = logging.getLogger(__name__)

RESOURCE = "/io/github/abhilashmuraleedharan/lapcare/ui/pages/hardware/page.ui"


@Gtk.Template(resource_path=RESOURCE)
class HardwarePage(Adw.Bin):
    __gtype_name__ = "LapcareHardwarePage"

    stack = Gtk.Template.Child()
    unavailable_status = Gtk.Template.Child()
    error_status = Gtk.Template.Child()
    row_family = Gtk.Template.Child()
    row_machine_type = Gtk.Template.Child()
    row_board = Gtk.Template.Child()
    row_bios_version = Gtk.Template.Child()
    row_bios_date = Gtk.Template.Child()
    row_cpu_model = Gtk.Template.Child()
    row_cpu_count = Gtk.Template.Child()
    row_memory = Gtk.Template.Child()
    pci_expander = Gtk.Template.Child()
    usb_expander = Gtk.Template.Child()

    def __init__(self, view_model: HardwareViewModel, **kwargs):
        super().__init__(**kwargs)
        self._vm = view_model
        self._device_rows: list[Adw.ActionRow] = []
        self._vm.connect("notify::state", self._on_state_changed)
        self._vm.load()

    def _on_state_changed(self, _vm, _pspec) -> None:
        state = self._vm.props.state
        if state == "ready":
            self._fill_ready()
        elif state == "unavailable":
            self.unavailable_status.set_description(
                f"{self._vm.props.unavailable_reason}\n{self._vm.props.unavailable_remedy}"
            )
        elif state == "error":
            self.error_status.set_description(self._vm.props.error_detail)
        self.stack.set_visible_child_name(state)

    def _fill_ready(self) -> None:
        for row, value in (
            (self.row_family, self._vm.props.family),
            (self.row_machine_type, self._vm.props.machine_type),
            (self.row_board, self._vm.props.board),
            (self.row_bios_version, self._vm.props.bios_version),
            (self.row_bios_date, self._vm.props.bios_date),
            (self.row_cpu_model, self._vm.props.cpu_model),
            (self.row_cpu_count, self._vm.props.cpu_count),
            (self.row_memory, self._vm.props.memory),
        ):
            row.set_subtitle(value)

        # Rebuild expander children (idempotent if load() ever reruns).
        for expander, row in [(r.get_ancestor(Adw.ExpanderRow), r) for r in self._device_rows]:
            if expander is not None:
                expander.remove(row)
        self._device_rows.clear()

        if self._vm.pci_note:
            self.pci_expander.set_subtitle(self._vm.pci_note)
            self.pci_expander.set_enable_expansion(False)
        else:
            self.pci_expander.set_subtitle(_("%d devices") % len(self._vm.pci_devices))
            self.pci_expander.set_enable_expansion(True)
        for pci in self._vm.pci_devices:
            row = Adw.ActionRow(
                title=f"{pci.vendor or '?'} — {pci.device or '?'}",
                subtitle=f"{pci.slot} · {pci.device_class or ''}".strip(" ·"),
                use_markup=False,
            )
            self.pci_expander.add_row(row)
            self._device_rows.append(row)

        if self._vm.usb_note:
            self.usb_expander.set_subtitle(self._vm.usb_note)
            self.usb_expander.set_enable_expansion(False)
        else:
            self.usb_expander.set_subtitle(_("%d devices") % len(self._vm.usb_devices))
            self.usb_expander.set_enable_expansion(True)
        for usb in self._vm.usb_devices:
            row = Adw.ActionRow(
                title=usb.name or _("Unknown device"),
                subtitle=f"{usb.vendor_id}:{usb.product_id} · "
                + _("bus %(b)s device %(d)s") % {"b": usb.bus, "d": usb.device},
                use_markup=False,
            )
            self.usb_expander.add_row(row)
            self._device_rows.append(row)
