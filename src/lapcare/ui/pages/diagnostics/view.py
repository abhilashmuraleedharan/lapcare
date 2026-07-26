# SPDX-License-Identifier: GPL-3.0-or-later
"""Diagnostics view: Run action, score header, one row per check.

The Run button carries the lock emblem (the run includes storage SMART via
the ADR-0006 helper — STYLEGUIDE: any control that can trigger a polkit
prompt is marked). Everything dynamic is code-built into results_container.
"""

import logging
from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from lapcare.ui.pages.diagnostics.view_model import CheckCard, DiagnosticsViewModel

log = logging.getLogger(__name__)

RESOURCE = "/io/github/abhilashmuraleedharan/lapcare/ui/pages/diagnostics/page.ui"


@Gtk.Template(resource_path=RESOURCE)
class DiagnosticsPage(Adw.Bin):
    __gtype_name__ = "LapcareDiagnosticsPage"

    toast_overlay = Gtk.Template.Child()
    busy_banner = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    results_container = Gtk.Template.Child()
    unavailable_status = Gtk.Template.Child()
    error_status = Gtk.Template.Child()

    def __init__(self, view_model: DiagnosticsViewModel, **kwargs):
        super().__init__(**kwargs)
        self._vm = view_model
        self._vm.connect("notify::state", self._on_state_changed)
        self._vm.connect("notify::busy-text", self._on_busy_changed)
        self._vm.connect("notify::toast-text", self._on_toast)
        self._vm.load()

    def _on_toast(self, _vm, _pspec) -> None:
        text = self._vm.props.toast_text
        if text:
            self.toast_overlay.add_toast(Adw.Toast(title=text))
            self._vm.props.toast_text = ""  # re-arm ("" notify is ignored here)

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
        self.results_container.set_sensitive(not busy)

    def _run_button(self, label: str) -> Gtk.Button:
        button = Gtk.Button(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        button.set_child(Adw.ButtonContent(label=label, icon_name="changes-prevent-symbolic"))
        button.add_css_class("suggested-action")
        button.add_css_class("pill")
        button.set_tooltip_text(
            _("Includes storage health, which requires administrator authorization.")
        )
        button.connect("clicked", lambda *_a: self._vm.run())
        return button

    def _on_export_clicked(self, _button) -> None:
        dialog = Gtk.FileDialog(initial_name=_("lapcare-report.md"))
        filters = Gio.ListStore.new(Gtk.FileFilter)
        for name, pattern in (
            (_("Markdown"), "*.md"),
            (_("HTML"), "*.html"),
            (_("JSON"), "*.json"),
        ):
            file_filter = Gtk.FileFilter()
            file_filter.set_name(name)
            file_filter.add_pattern(pattern)
            filters.append(file_filter)
        dialog.set_filters(filters)
        dialog.save(self.get_root(), None, self._on_export_chosen)

    def _on_export_chosen(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            file = dialog.save_finish(result)
        except GLib.Error:  # dismissed — a legitimate choice, no toast
            return
        path = file.get_path()
        if path:
            self._vm.export(path)

    def _check_row(self, card: CheckCard) -> Gtk.Widget:
        if not card.evidence:
            row = Adw.ActionRow(title=card.title, subtitle=card.subtitle, use_markup=False)
            self._add_status_suffix(row, card)
            return row
        expander = Adw.ExpanderRow(title=card.title, subtitle=card.subtitle, use_markup=False)
        self._add_status_suffix(expander, card)
        for label, value in card.evidence:
            detail = Adw.ActionRow(title=label, subtitle=value, use_markup=False)
            detail.add_css_class("property")
            expander.add_row(detail)
        return expander

    @staticmethod
    def _add_status_suffix(row, card: CheckCard) -> None:
        status = Gtk.Label(label=card.status_text, valign=Gtk.Align.CENTER)
        status.add_css_class(card.status_css)
        row.add_suffix(status)

    def _fill_ready(self) -> None:
        child = self.results_container.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.results_container.remove(child)
            child = nxt

        if not self._vm.cards:
            intro = Adw.StatusPage(
                icon_name="emblem-default-symbolic",
                title=_("Check This Machine's Health"),
                description=_(
                    "Five quick checks: battery wear, storage health, firmware "
                    "currency, temperatures, and disk space. Takes a few seconds."
                ),
            )
            intro.set_child(self._run_button(_("Run Diagnostics")))
            intro.set_vexpand(True)
            self.results_container.append(intro)
            return

        score = Adw.PreferencesGroup(title=_("Health Score"))
        actions = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        if self._vm.can_export:
            export = Gtk.Button()
            export.set_child(
                Adw.ButtonContent(label=_("Export…"), icon_name="document-save-symbolic")
            )
            export.set_tooltip_text(
                _("Save this report as Markdown, HTML, or JSON. Identifiers are excluded.")
            )
            export.connect("clicked", self._on_export_clicked)
            actions.append(export)
        actions.append(self._run_button(_("Run Again")))
        score.set_header_suffix(actions)
        score_row = Adw.ActionRow(
            title=self._vm.props.score_text, subtitle=self._vm.props.coverage_text
        )
        score_row.add_css_class("property")
        score.add(score_row)
        self.results_container.append(score)

        checks = Adw.PreferencesGroup(title=_("Checks"))
        for card in self._vm.cards:
            checks.add(self._check_row(card))
        self.results_container.append(checks)
