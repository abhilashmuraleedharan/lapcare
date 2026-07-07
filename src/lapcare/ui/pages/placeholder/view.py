# SPDX-License-Identifier: GPL-3.0-or-later
"""Reference page view: binds the four-state stack to its view-model.

Thin by contract: forwards debug-switcher clicks to the view-model and
mirrors view-model state into widgets. No business logic.

LAPCARE_SMOKE=1 makes the page cycle through all four states automatically
(used by the xvfb smoke test to exercise every state's widgets).
"""

import logging
import os

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from lapcare.ui.pages.placeholder.view_model import STATES, PlaceholderViewModel

log = logging.getLogger(__name__)

RESOURCE = "/io/github/abhilashmuraleedharan/lapcare/ui/pages/placeholder/page.ui"


@Gtk.Template(resource_path=RESOURCE)
class PlaceholderPage(Adw.Bin):
    __gtype_name__ = "LapcarePlaceholderPage"

    stack = Gtk.Template.Child()
    unavailable_status = Gtk.Template.Child()
    error_status = Gtk.Template.Child()

    def __init__(self, view_model: PlaceholderViewModel, **kwargs):
        super().__init__(**kwargs)
        self._vm = view_model
        self._vm.connect("notify::state", self._on_state_changed)
        self._sync()

        if os.environ.get("LAPCARE_SMOKE") == "1":
            self._smoke_steps = len(STATES)
            GLib.timeout_add(150, self._smoke_advance)

    def _on_state_changed(self, _vm, _pspec) -> None:
        self._sync()

    def _sync(self) -> None:
        state = self._vm.props.state
        if state == "unavailable":
            self.unavailable_status.set_description(
                f"{self._vm.props.unavailable_reason}\n{self._vm.props.unavailable_remedy}"
            )
        elif state == "error":
            self.error_status.set_description(self._vm.props.error_detail)
        self.stack.set_visible_child_name(state)

    # Debug switcher (wired in page.blp)

    @Gtk.Template.Callback()
    def _on_demo_loading(self, _button) -> None:
        self._vm.show_loading()

    @Gtk.Template.Callback()
    def _on_demo_ready(self, _button) -> None:
        self._vm.show_ready()

    @Gtk.Template.Callback()
    def _on_demo_unavailable(self, _button) -> None:
        self._vm.demo_unavailable()

    @Gtk.Template.Callback()
    def _on_demo_error(self, _button) -> None:
        self._vm.demo_error()

    # Smoke-test hook

    def _smoke_advance(self) -> bool:
        self._vm.advance()
        self._smoke_steps -= 1
        if self._smoke_steps <= 0:
            log.info("smoke: cycled all states")
            return False  # GLib.SOURCE_REMOVE
        return True
