# SPDX-License-Identifier: GPL-3.0-or-later
"""Dashboard view: binds the view-model's finalized strings into rows.

Thin by contract — no hardware logic here. The view triggers the initial
load; the view-model does everything else.
"""

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from lapcare.ui.pages.dashboard.view_model import DashboardViewModel

log = logging.getLogger(__name__)

RESOURCE = "/io/github/abhilashmuraleedharan/lapcare/ui/pages/dashboard/page.ui"


@Gtk.Template(resource_path=RESOURCE)
class DashboardPage(Adw.Bin):
    __gtype_name__ = "LapcareDashboardPage"

    banner = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    unavailable_status = Gtk.Template.Child()
    error_status = Gtk.Template.Child()
    health_group = Gtk.Template.Child()
    row_health = Gtk.Template.Child()
    row_model = Gtk.Template.Child()
    row_machine_type = Gtk.Template.Child()
    row_vendor = Gtk.Template.Child()
    row_bios = Gtk.Template.Child()
    row_distro = Gtk.Template.Child()
    row_kernel = Gtk.Template.Child()
    row_uptime = Gtk.Template.Child()

    def __init__(self, view_model: DashboardViewModel, **kwargs):
        super().__init__(**kwargs)
        self._vm = view_model
        self._vm.connect("notify::state", self._on_state_changed)
        self._vm.connect("notify::health-score", self._on_health_changed)
        self._vm.load()

    def _on_health_changed(self, _vm, _pspec) -> None:
        # Arrives independently of the identity rows (separate submit).
        score = self._vm.props.health_score
        if score:
            self.row_health.set_title(score)
            self.row_health.set_subtitle(self._vm.props.health_coverage)
            self.health_group.set_visible(True)

    def _on_state_changed(self, _vm, _pspec) -> None:
        state = self._vm.props.state
        if state == "ready":
            for row, value in (
                (self.row_model, self._vm.props.model),
                (self.row_machine_type, self._vm.props.machine_type),
                (self.row_vendor, self._vm.props.vendor),
                (self.row_bios, self._vm.props.bios),
                (self.row_distro, self._vm.props.distro),
                (self.row_kernel, self._vm.props.kernel),
                (self.row_uptime, self._vm.props.uptime),
            ):
                row.set_subtitle(value)
            self.banner.set_revealed(not self._vm.props.is_thinkpad)
        elif state == "unavailable":
            self.unavailable_status.set_description(
                f"{self._vm.props.unavailable_reason}\n{self._vm.props.unavailable_remedy}"
            )
        elif state == "error":
            self.error_status.set_description(self._vm.props.error_detail)
        self.stack.set_visible_child_name(state)
