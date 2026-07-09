# SPDX-License-Identifier: GPL-3.0-or-later
"""Battery view: builds one preferences group per battery from the cards.

Dynamic (dual-battery) content is code-built into battery_container; the
blueprint provides the four-state shell and the degradation banner.
"""

import logging
from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from lapcare.core.battery_analysis import HealthClass
from lapcare.ui.pages.battery.view_model import BatteryViewModel
from lapcare.ui.widgets.wear_chart import WearChart

log = logging.getLogger(__name__)

RESOURCE = "/io/github/abhilashmuraleedharan/lapcare/ui/pages/battery/page.ui"

_HEALTH_CSS = {
    HealthClass.GOOD: "success",
    HealthClass.FAIR: "warning",
    HealthClass.POOR: "error",
    HealthClass.UNKNOWN: "dim-label",
}


@Gtk.Template(resource_path=RESOURCE)
class BatteryPage(Adw.Bin):
    __gtype_name__ = "LapcareBatteryPage"

    status_banner = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    battery_container = Gtk.Template.Child()
    unavailable_status = Gtk.Template.Child()
    error_status = Gtk.Template.Child()

    def __init__(self, view_model: BatteryViewModel, **kwargs):
        super().__init__(**kwargs)
        self._vm = view_model
        self._vm.connect("notify::state", self._on_state_changed)
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

    def _property_row(self, title: str, subtitle: str) -> Adw.ActionRow:
        row = Adw.ActionRow(title=title, subtitle=subtitle, use_markup=False)
        row.add_css_class("property")
        return row

    def _fill_ready(self) -> None:
        note = self._vm.props.status_note
        self.status_banner.set_title(note)
        self.status_banner.set_revealed(bool(note))

        child = self.battery_container.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.battery_container.remove(child)
            child = nxt

        for card in self._vm.cards:
            group = Adw.PreferencesGroup(title=card.title)

            charge = self._property_row(_("Charge"), card.charge_text)
            if card.time_text:
                charge.set_subtitle(f"{card.charge_text} · {card.time_text}")
            group.add(charge)

            health = self._property_row(_("Health"), f"{card.health_text} · {card.wear_text}")
            health.add_css_class(_HEALTH_CSS[card.health_class])
            group.add(health)

            group.add(self._property_row(_("Cycle Count"), card.cycles_text))
            group.add(self._property_row(_("Capacity"), card.capacity_text))

            if card.history:
                chart_row = Adw.PreferencesRow(activatable=False)
                chart = WearChart()
                chart.set_points(card.history)
                chart.set_margin_top(8)
                chart.set_margin_bottom(8)
                chart.set_margin_start(8)
                chart.set_margin_end(8)
                chart_row.set_child(chart)
                chart_group = Adw.PreferencesGroup(title=_("Wear Over Time"))
                chart_group.add(chart_row)
                self.battery_container.append(group)
                self.battery_container.append(chart_group)
            else:
                self.battery_container.append(group)
