# SPDX-License-Identifier: GPL-3.0-or-later
"""Firmware view: device rows + release rows with Install buttons.

Dynamic (per-device) content is code-built into devices_container; the
blueprint provides the four-state shell, three banners (busy / flow /
reboot-required), and the toast overlay. Install buttons carry the lock
emblem (STYLEGUIDE: any control that triggers a polkit prompt is marked).
"""

import logging
from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from lapcare.ui.pages.firmware.view_model import URGENCY_TEXT, FirmwareViewModel

log = logging.getLogger(__name__)

RESOURCE = "/io/github/abhilashmuraleedharan/lapcare/ui/pages/firmware/page.ui"


@Gtk.Template(resource_path=RESOURCE)
class FirmwarePage(Adw.Bin):
    __gtype_name__ = "LapcareFirmwarePage"

    toast_overlay = Gtk.Template.Child()
    busy_banner = Gtk.Template.Child()
    flow_banner = Gtk.Template.Child()
    reboot_banner = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    devices_container = Gtk.Template.Child()
    unavailable_status = Gtk.Template.Child()
    error_status = Gtk.Template.Child()

    def __init__(self, view_model: FirmwareViewModel, **kwargs):
        super().__init__(**kwargs)
        self._vm = view_model
        self._vm.connect("notify::state", self._on_state_changed)
        self._vm.connect("notify::busy-text", self._on_busy_changed)
        self._vm.connect("notify::flow-banner", self._on_flow_changed)
        self._vm.connect("notify::reboot-banner", self._on_reboot_changed)
        self._vm.connect("notify::toast-text", self._on_toast)
        self._vm.load()
        self._vm.start_live_updates()

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
        # One operation at a time: refresh/install actions are inert while busy.
        self.devices_container.set_sensitive(not busy)

    def _on_flow_changed(self, _vm, _pspec) -> None:
        note = self._vm.props.flow_banner
        self.flow_banner.set_title(note)
        self.flow_banner.set_revealed(bool(note))

    def _on_reboot_changed(self, _vm, _pspec) -> None:
        note = self._vm.props.reboot_banner
        self.reboot_banner.set_title(note)
        self.reboot_banner.set_revealed(bool(note))

    def _on_toast(self, _vm, _pspec) -> None:
        text = self._vm.props.toast_text
        if text:
            self.toast_overlay.add_toast(Adw.Toast(title=text))
            self._vm.props.toast_text = ""  # re-arm ("" notify is ignored here)

    def _release_row(self, device_id: str, release) -> Adw.ActionRow:
        title = _("Version %s") % release.version
        if release.urgency in URGENCY_TEXT:
            title = f"{title} · {URGENCY_TEXT[release.urgency]}"
        row = Adw.ActionRow(title=title, subtitle=release.summary or release.name or "")
        button = Gtk.Button(valign=Gtk.Align.CENTER)
        content = Adw.ButtonContent(label=_("Install…"), icon_name="changes-prevent-symbolic")
        button.set_child(content)
        button.add_css_class("suggested-action")
        button.set_tooltip_text(_("Installing firmware requires administrator authorization."))
        button.connect("clicked", lambda *_a: self._vm.request_install(device_id, release))
        row.add_suffix(button)
        return row

    def _fill_ready(self) -> None:
        child = self.devices_container.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.devices_container.remove(child)
            child = nxt

        group = Adw.PreferencesGroup(title=_("Firmware Devices"))
        refresh = Gtk.Button(valign=Gtk.Align.CENTER)
        refresh.set_child(
            Adw.ButtonContent(label=_("Check for Updates"), icon_name="view-refresh-symbolic")
        )
        refresh.set_tooltip_text(_("Download the latest update metadata from LVFS."))
        refresh.connect("clicked", lambda *_a: self._vm.refresh_metadata())
        group.set_header_suffix(refresh)

        for card in self._vm.cards:
            if card.releases:
                expander = Adw.ExpanderRow(
                    title=card.title,
                    subtitle=_("%(version)s → %(new)s available")
                    % {"version": card.version_text, "new": card.releases[0].version},
                )
                expander.set_expanded(True)
                for release in card.releases:
                    expander.add_row(self._release_row(card.id, release))
                group.add(expander)
                continue

            row = Adw.ActionRow(title=card.title)
            row.add_css_class("property")
            if card.upgrade_note:
                row.set_subtitle(f"{card.version_text} — {card.upgrade_note}")
            elif card.update_error:
                row.set_subtitle(
                    f"{card.version_text} — " + _("last update failed: %s") % card.update_error
                )
            elif card.updatable:
                row.set_subtitle(f"{card.version_text} — " + _("up to date"))
            else:
                row.set_subtitle(f"{card.version_text} — " + _("updates not supported"))
            if card.subtitle:
                row.set_tooltip_text(card.subtitle)
            group.add(row)

        self.devices_container.append(group)

        if self._vm.props.result_text:
            done = Adw.PreferencesGroup(title=_("Last Update"))
            note = Adw.ActionRow(title=self._vm.props.result_text)
            note.add_css_class("property")
            done.add(note)
            self.devices_container.append(done)
