# SPDX-License-Identifier: GPL-3.0-or-later
"""Battery wear analysis and health classification. Pure functions.

The rubric is deliberately transparent (constitution: every assessment must
be explainable in the UI):

- wear % = (1 - capacity_full / capacity_design) x 100, unit-agnostic —
  both sysfs unit families divide out.
- Fresh or recently recalibrated packs sometimes report full above design
  (fixture: synthetic-pathological BAT0) → wear clamps to 0.0, never
  negative.
- Classification thresholds (conservative, revisited against the fixture
  corpus at M5 calibration review): GOOD below 15%, FAIR 15-30%, POOR 30%+.
"""

from __future__ import annotations

import datetime
from enum import Enum

from lapcare.core.models import BatteryWear, WearSnapshot

GOOD_MAX_WEAR = 15.0
FAIR_MAX_WEAR = 30.0


class HealthClass(Enum):
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNKNOWN = "unknown"


def wear_percent(capacity_full: int | None, capacity_design: int | None) -> float | None:
    """Wear as a percentage of design capacity; None when unknowable."""
    if capacity_full is None or capacity_design is None or capacity_design <= 0:
        return None
    wear = (1.0 - capacity_full / capacity_design) * 100.0
    return max(wear, 0.0)


def classify_wear(wear: float | None) -> HealthClass:
    if wear is None:
        return HealthClass.UNKNOWN
    if wear < GOOD_MAX_WEAR:
        return HealthClass.GOOD
    if wear < FAIR_MAX_WEAR:
        return HealthClass.FAIR
    return HealthClass.POOR


def snapshot_from_wear(wear: BatteryWear, day: datetime.date | None = None) -> WearSnapshot:
    """Build today's history snapshot for one battery."""
    d = day or datetime.date.today()
    return WearSnapshot(
        day=d.isoformat(),
        battery_name=wear.name,
        wear_percent=wear_percent(wear.capacity_full, wear.capacity_design),
        cycle_count=wear.cycle_count,
        capacity_full=wear.capacity_full,
        capacity_design=wear.capacity_design,
    )
