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
from gi.repository import Adw, Gtk

from lapcare.ui.pages.diagnostics.view_model import CheckCard, DiagnosticsViewModel

log = logging.getLogger(__name__)

RESOURCE = "/io/github/abhilashmuraleedharan/lapcare/ui/pages/diagnostics/page.ui"


@Gtk.Template(resource_path=RESOURCE)
class DiagnosticsPage(Adw.Bin):
    __gtype_name__ = "LapcareDiagnosticsPage"

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

    def _check_row(self, card: CheckCard) -> Gtk.Widget:
        if not card.evidence:
            row = Adw.ActionRow(title=card.title, subtitle=card.subtitle)
            self._add_status_suffix(row, card)
            return row
        expander = Adw.ExpanderRow(title=card.title, subtitle=card.subtitle)
        self._add_status_suffix(expander, card)
        for label, value in card.evidence:
            detail = Adw.ActionRow(title=label, subtitle=value)
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
        score.set_header_suffix(self._run_button(_("Run Again")))
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
