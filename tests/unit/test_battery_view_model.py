# SPDX-License-Identifier: GPL-3.0-or-later
"""Battery view-model: real fixtures, degradation policy, snapshot recording."""

from __future__ import annotations

from pathlib import Path

from lapcare.core.battery_analysis import HealthClass
from lapcare.core.errors import ProviderUnavailable
from lapcare.core.models import Availability, BatteryState, BatteryStatus
from lapcare.platform.history import SqliteHistoryStore
from lapcare.providers.battery_sysfs import BatterySysfs
from lapcare.ui.pages.battery.view_model import BatteryViewModel, format_capacity

from ..providers.conftest import fixture_root
from .test_dashboard_view_model import ImmediateScheduler


class FakeStatus:
    def __init__(self, batteries: list[BatteryStatus] | None) -> None:
        self._batteries = batteries

    def availability(self) -> Availability:
        return Availability.OK if self._batteries is not None else Availability.TOOL_MISSING

    async def read_status(self) -> list[BatteryStatus]:
        if self._batteries is None:
            raise ProviderUnavailable("upower", Availability.TOOL_MISSING, tool="upower")
        return self._batteries

    def subscribe(self, on_change) -> None:  # pragma: no cover - not exercised here
        pass


def _vm(tmp_path: Path, machine: str, status: FakeStatus) -> BatteryViewModel:
    return BatteryViewModel(
        ImmediateScheduler(),
        wear=BatterySysfs(root=fixture_root("battery_sysfs", machine)),
        status=status,
        history=SqliteHistoryStore(db_path=tmp_path / "history.db"),
    )


def test_ready_with_e16_fixture_and_live_status(tmp_path: Path) -> None:
    status = FakeStatus(
        [
            BatteryStatus(
                name="BAT0",
                state=BatteryState.NOT_CHARGING,
                percentage=79.0,
                energy_rate_w=0.0,
            )
        ]
    )
    vm = _vm(tmp_path, "thinkpad-e16-gen2", status)
    vm.load()
    assert vm.props.state == "ready"
    assert vm.props.status_note == ""
    (card,) = vm.cards
    assert card.name == "BAT0"
    assert "Sunwoda" in card.title
    assert card.charge_text == "79% · Not charging"
    assert card.health_class is HealthClass.GOOD
    assert card.wear_text == "4.8% worn"
    assert card.cycles_text == "92"
    assert "54.3 Wh" in card.capacity_text and "57.0 Wh" in card.capacity_text
    # Today's snapshot was recorded and is in the chart data.
    assert len(card.history) == 1
    assert round(card.history[0][1], 2) == 4.75


def test_status_unavailable_degrades_to_note_not_error(tmp_path: Path) -> None:
    vm = _vm(tmp_path, "thinkpad-e16-gen2", FakeStatus(None))
    vm.load()
    assert vm.props.state == "ready"  # wear still shows
    assert "upower" in vm.props.status_note
    (card,) = vm.cards
    assert card.charge_text == "—"


def test_dual_battery_cards(tmp_path: Path) -> None:
    vm = _vm(tmp_path, "synthetic-pathological", FakeStatus([]))
    vm.load()
    assert vm.props.state == "ready"
    assert [c.name for c in vm.cards] == ["BAT0", "BAT1"]
    bat0, bat1 = vm.cards
    assert bat0.wear_text == "0.0% worn"  # full-above-design clamped
    assert bat1.cycles_text == "—"  # -1 normalized away


def test_no_batteries_is_unavailable(tmp_path: Path) -> None:
    empty_root = tmp_path / "empty"
    (empty_root / "sys/class/power_supply").mkdir(parents=True)
    vm = BatteryViewModel(
        ImmediateScheduler(),
        wear=BatterySysfs(root=empty_root),
        status=FakeStatus([]),
        history=SqliteHistoryStore(db_path=tmp_path / "history.db"),
    )
    vm.load()
    assert vm.props.state == "unavailable"
    assert "No batteries" in vm.props.unavailable_reason


def test_history_accumulates_across_loads(tmp_path: Path) -> None:
    vm = _vm(tmp_path, "thinkpad-e16-gen2", FakeStatus(None))
    vm.load()
    vm.load()  # same day: idempotent, still one point
    (card,) = vm.cards
    assert len(card.history) == 1


def test_format_capacity() -> None:
    from lapcare.core.models import CapacityUnit

    assert format_capacity(None, None) == "—"
    assert format_capacity(54_290_000, CapacityUnit.MICRO_WATT_HOURS) == "54.3 Wh"
    assert format_capacity(4_200_000, CapacityUnit.MICRO_AMP_HOURS) == "4200 mAh"
