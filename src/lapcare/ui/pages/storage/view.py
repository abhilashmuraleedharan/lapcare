# SPDX-License-Identifier: GPL-3.0-or-later
"""Storage view: device rows, expanding into SMART detail after health read.

Dynamic (per-device) content is code-built into devices_container; the
blueprint provides the four-state shell, the busy banner, and the toast
overlay. The Read Health button carries the lock emblem (STYLEGUIDE: any
control that triggers a polkit prompt is marked)."""

import logging
from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from lapcare.ui.pages.storage.view_model import StorageCard, StorageViewModel

log = logging.getLogger(__name__)

RESOURCE = "/io/github/abhilashmuraleedharan/lapcare/ui/pages/storage/page.ui"


@Gtk.Template(resource_path=RESOURCE)
class StoragePage(Adw.Bin):
    __gtype_name__ = "LapcareStoragePage"

    toast_overlay = Gtk.Template.Child()
    busy_banner = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    devices_container = Gtk.Template.Child()
    unavailable_status = Gtk.Template.Child()
    error_status = Gtk.Template.Child()

    def __init__(self, view_model: StorageViewModel, **kwargs):
        super().__init__(**kwargs)
        self._vm = view_model
        self._vm.connect("notify::state", self._on_state_changed)
        self._vm.connect("notify::busy-text", self._on_busy_changed)
        self._vm.connect("notify::toast-text", self._on_toast)
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

    def _on_busy_changed(self, _vm, _pspec) -> None:
        busy = self._vm.props.busy_text
        self.busy_banner.set_title(busy)
        self.busy_banner.set_revealed(bool(busy))
        self.devices_container.set_sensitive(not busy)

    def _on_toast(self, _vm, _pspec) -> None:
        text = self._vm.props.toast_text
        if text:
            self.toast_overlay.add_toast(Adw.Toast(title=text))
            self._vm.props.toast_text = ""  # re-arm ("" notify is ignored here)

    def _device_row(self, card: StorageCard) -> Gtk.Widget:
        if not card.health_rows:
            row = Adw.ActionRow(title=card.title, subtitle=card.subtitle, use_markup=False)
            row.add_css_class("property")
            if card.health_note:
                row.set_subtitle(f"{card.subtitle} — {card.health_note}")
            return row

        expander = Adw.ExpanderRow(title=card.title, subtitle=card.subtitle, use_markup=False)
        summary = Gtk.Label(label=card.health_summary, valign=Gtk.Align.CENTER)
        summary.add_css_class("error" if card.health_failed else "success")
        expander.add_suffix(summary)
        expander.set_expanded(True)
        for label, value in card.health_rows:
            detail = Adw.ActionRow(title=label, subtitle=value, use_markup=False)
            detail.add_css_class("property")
            expander.add_row(detail)
        return expander

    def _fill_ready(self) -> None:
        child = self.devices_container.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.devices_container.remove(child)
            child = nxt

        group = Adw.PreferencesGroup(title=_("Storage Devices"))
        health = Gtk.Button(valign=Gtk.Align.CENTER)
        health.set_child(
            Adw.ButtonContent(label=_("Read Health"), icon_name="changes-prevent-symbolic")
        )
        health.set_tooltip_text(_("Reading SMART health requires administrator authorization."))
        health.connect("clicked", lambda *_a: self._vm.read_health())
        group.set_header_suffix(health)

        for card in self._vm.cards:
            group.add(self._device_row(card))
        self.devices_container.append(group)
