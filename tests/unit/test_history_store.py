# SPDX-License-Identifier: GPL-3.0-or-later
"""SQLite HistoryStore: idempotency, restart survival, ordering, isolation."""

from __future__ import annotations

from pathlib import Path

from lapcare.core.models import WearSnapshot
from lapcare.platform.history import SqliteHistoryStore


def _snap(day: str, battery: str = "BAT0", wear: float = 4.75) -> WearSnapshot:
    return WearSnapshot(
        day=day,
        battery_name=battery,
        wear_percent=wear,
        cycle_count=92,
        capacity_full=54_290_000,
        capacity_design=57_000_000,
    )


def test_record_and_read_roundtrip(tmp_path: Path) -> None:
    store = SqliteHistoryStore(db_path=tmp_path / "history.db")
    store.record_wear(_snap("2026-07-07"))
    (snap,) = store.wear_history("BAT0")
    assert snap == _snap("2026-07-07")


def test_same_day_is_idempotent_replace(tmp_path: Path) -> None:
    store = SqliteHistoryStore(db_path=tmp_path / "history.db")
    store.record_wear(_snap("2026-07-07", wear=4.75))
    store.record_wear(_snap("2026-07-07", wear=4.80))  # later reading same day
    (snap,) = store.wear_history("BAT0")
    assert snap.wear_percent == 4.80


def test_history_survives_restart(tmp_path: Path) -> None:
    # M2 acceptance criterion: a NEW store instance on the same path sees
    # everything the old one wrote.
    path = tmp_path / "history.db"
    SqliteHistoryStore(db_path=path).record_wear(_snap("2026-07-06"))
    SqliteHistoryStore(db_path=path).record_wear(_snap("2026-07-07"))
    days = [s.day for s in SqliteHistoryStore(db_path=path).wear_history("BAT0")]
    assert days == ["2026-07-06", "2026-07-07"]


def test_limit_keeps_most_recent_ascending(tmp_path: Path) -> None:
    store = SqliteHistoryStore(db_path=tmp_path / "history.db")
    for day in ("2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04"):
        store.record_wear(_snap(day))
    days = [s.day for s in store.wear_history("BAT0", limit=2)]
    assert days == ["2026-07-03", "2026-07-04"]


def test_batteries_are_isolated(tmp_path: Path) -> None:
    store = SqliteHistoryStore(db_path=tmp_path / "history.db")
    store.record_wear(_snap("2026-07-07", battery="BAT0"))
    store.record_wear(_snap("2026-07-07", battery="BAT1", wear=12.0))
    assert [s.battery_name for s in store.wear_history("BAT0")] == ["BAT0"]
    (bat1,) = store.wear_history("BAT1")
    assert bat1.wear_percent == 12.0


def test_creates_parent_directory(tmp_path: Path) -> None:
    store = SqliteHistoryStore(db_path=tmp_path / "deep" / "nested" / "history.db")
    store.record_wear(_snap("2026-07-07"))
    assert store.wear_history("BAT0")
