# SPDX-License-Identifier: GPL-3.0-or-later
"""Battery view-model: wear analysis + live status + history recording.

Panel degradation policy: wear data (sysfs) is the page's core — its failure
fails the page. Live status (UPower) degrades to a note (``status_note``):
containers/CI have no system bus, and the page must still show wear there.
Recording today's snapshot and reading history happen inside the load
coroutine (HistoryStore's contract: scheduler context).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from gettext import gettext as _
from typing import TYPE_CHECKING

from gi.repository import GLib, GObject

from lapcare.core.battery_analysis import (
    HealthClass,
    classify_wear,
    snapshot_from_wear,
    wear_percent,
)
from lapcare.core.errors import LapcareError
from lapcare.core.models import (
    BatteryState,
    BatteryStatus,
    BatteryWear,
    CapacityUnit,
)
from lapcare.ui.pages.base_view_model import PageViewModel
from lapcare.ui.pages.dashboard.view_model import format_uptime

if TYPE_CHECKING:
    from lapcare.core.ports import (
        BatteryStatusProvider,
        BatteryWearProvider,
        HistoryStore,
        Scheduler,
    )

log = logging.getLogger(__name__)

PLACEHOLDER = "—"
_RELOAD_DEBOUNCE_MS = 700

_STATE_TEXT = {
    BatteryState.CHARGING: _("Charging"),
    BatteryState.DISCHARGING: _("Discharging"),
    BatteryState.NOT_CHARGING: _("Not charging"),
    BatteryState.FULL: _("Full"),
    BatteryState.EMPTY: _("Empty"),
    BatteryState.UNKNOWN: _("Unknown"),
}

_HEALTH_TEXT = {
    HealthClass.GOOD: _("Good"),
    HealthClass.FAIR: _("Fair"),
    HealthClass.POOR: _("Poor"),
    HealthClass.UNKNOWN: _("Unknown"),
}


def format_capacity(value: int | None, unit: CapacityUnit | None) -> str:
    if value is None or unit is None:
        return PLACEHOLDER
    if unit is CapacityUnit.MICRO_WATT_HOURS:
        return _("%.1f Wh") % (value / 1_000_000)
    return _("%.0f mAh") % (value / 1_000)


@dataclass
class BatteryCard:
    """Finalized display data for one battery (the view only copies it)."""

    name: str
    title: str
    charge_text: str = PLACEHOLDER
    time_text: str = ""
    health_text: str = PLACEHOLDER
    health_class: HealthClass = HealthClass.UNKNOWN
    wear_text: str = PLACEHOLDER
    cycles_text: str = PLACEHOLDER
    capacity_text: str = PLACEHOLDER
    history: list[tuple[str, float]] = field(default_factory=list)


class BatteryViewModel(PageViewModel):
    __gtype_name__ = "LapcareBatteryViewModel"

    status_note = GObject.Property(type=str, default="")

    def __init__(
        self,
        scheduler: Scheduler,
        wear: BatteryWearProvider,
        status: BatteryStatusProvider,
        history: HistoryStore,
    ) -> None:
        super().__init__()
        self._scheduler = scheduler
        self._wear = wear
        self._status = status
        self._history = history
        self._reload_pending = False
        self.cards: list[BatteryCard] = []

    def load(self) -> None:
        self.show_loading()
        self._scheduler.submit(self._gather(), self._apply, self.handle_error)

    def start_live_updates(self) -> None:
        """Subscribe to status changes; debounced reloads. Main thread only."""
        try:
            self._status.subscribe(self._on_status_changed)
        except LapcareError as exc:
            log.debug("no live updates: %s", exc)

    def _on_status_changed(self) -> None:
        if self._reload_pending:
            return
        self._reload_pending = True

        def _reload() -> bool:
            self._reload_pending = False
            self._scheduler.submit(self._gather(), self._apply, self.handle_error)
            return False  # GLib.SOURCE_REMOVE

        GLib.timeout_add(_RELOAD_DEBOUNCE_MS, _reload)

    async def _gather(
        self,
    ) -> tuple[list[BatteryWear], list[BatteryStatus] | None, dict[str, list[tuple[str, float]]]]:
        wear_list = await self._wear.list_batteries()

        status_list: list[BatteryStatus] | None
        try:
            status_list = await self._status.read_status()
        except LapcareError as exc:
            # The container/CI norm: no system bus. Wear must still show.
            log.debug("status degraded: %s", exc)
            status_list = None

        history: dict[str, list[tuple[str, float]]] = {}
        for wear in wear_list:
            self._history.record_wear(snapshot_from_wear(wear))
            history[wear.name] = [
                (s.day, s.wear_percent)
                for s in self._history.wear_history(wear.name)
                if s.wear_percent is not None
            ]
        return wear_list, status_list, history

    def _apply(
        self,
        data: tuple[
            list[BatteryWear], list[BatteryStatus] | None, dict[str, list[tuple[str, float]]]
        ],
    ) -> None:
        wear_list, status_list, history = data

        if not wear_list:
            self.show_unavailable(
                _("No batteries detected on this system."),
                _("Nothing to do — battery features need a battery."),
            )
            return

        status_by_name = {s.name: s for s in status_list or []}
        self.props.status_note = (
            ""
            if status_list is not None
            else _("Live charge status unavailable — install/start the 'upower' service.")
        )

        cards: list[BatteryCard] = []
        for wear in wear_list:
            wear_pct = wear_percent(wear.capacity_full, wear.capacity_design)
            health = classify_wear(wear_pct)
            hardware = " — ".join(x for x in (wear.manufacturer, wear.model_name) if x)
            card = BatteryCard(
                name=wear.name,
                title=wear.name if not hardware else f"{wear.name} · {hardware}",
                health_text=_HEALTH_TEXT[health],
                health_class=health,
                wear_text=_("%.1f%% worn") % wear_pct if wear_pct is not None else PLACEHOLDER,
                cycles_text=str(wear.cycle_count) if wear.cycle_count is not None else PLACEHOLDER,
                capacity_text=_("%(full)s of %(design)s design")
                % {
                    "full": format_capacity(wear.capacity_full, wear.capacity_unit),
                    "design": format_capacity(wear.capacity_design, wear.capacity_unit),
                },
                history=history.get(wear.name, []),
            )
            status = status_by_name.get(wear.name)
            if status is not None:
                pct = f"{status.percentage:.0f}%" if status.percentage is not None else PLACEHOLDER
                card.charge_text = f"{pct} · {_STATE_TEXT[status.state]}"
                if status.time_to_empty_s:
                    card.time_text = _("%s until empty") % format_uptime(status.time_to_empty_s)
                elif status.time_to_full_s:
                    card.time_text = _("%s until full") % format_uptime(status.time_to_full_s)
            cards.append(card)

        self.cards = cards
        log.debug("battery ready count=%d live=%s", len(cards), status_list is not None)
        self.show_ready()
