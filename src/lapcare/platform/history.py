# SPDX-License-Identifier: GPL-3.0-or-later
"""Wear-history persistence: SQLite under the XDG data dir.

Implements core.ports.HistoryStore. One row per (day, battery);
INSERT OR REPLACE makes the daily snapshot idempotent. Connections are
opened per operation — trivial rates (one write per day, one read per page
load) buy total freedom from cross-thread connection rules under both
ADR-0007 scheduler mechanisms. Methods are synchronous; the port's contract
says call them from scheduler context.

Nothing secret is stored (constitution: battery names, capacities, cycle
counts, dates).
"""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

from lapcare.core.models import WearSnapshot

log = logging.getLogger(__name__)

_CREATE = """
CREATE TABLE IF NOT EXISTS wear_history (
    day TEXT NOT NULL,
    battery_name TEXT NOT NULL,
    wear_percent REAL,
    cycle_count INTEGER,
    capacity_full INTEGER,
    capacity_design INTEGER,
    PRIMARY KEY (day, battery_name)
)
"""


def default_db_path() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")
    return Path(base) / "lapcare" / "history.db"


class SqliteHistoryStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self._path = db_path or default_db_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.execute(_CREATE)
        return conn

    def record_wear(self, snapshot: WearSnapshot) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO wear_history VALUES (?, ?, ?, ?, ?, ?)",
                (
                    snapshot.day,
                    snapshot.battery_name,
                    snapshot.wear_percent,
                    snapshot.cycle_count,
                    snapshot.capacity_full,
                    snapshot.capacity_design,
                ),
            )
        log.debug("recorded wear snapshot day=%s battery=%s", snapshot.day, snapshot.battery_name)

    def wear_history(self, battery_name: str, limit: int = 365) -> list[WearSnapshot]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT day, battery_name, wear_percent, cycle_count,"
                " capacity_full, capacity_design FROM wear_history"
                " WHERE battery_name = ? ORDER BY day DESC LIMIT ?",
                (battery_name, limit),
            ).fetchall()
        # DESC + LIMIT selects the most recent N; present them ascending.
        return [WearSnapshot(*row) for row in reversed(rows)]
