# SPDX-License-Identifier: GPL-3.0-or-later
"""Wear math and health classification — incl. the fixture-corpus quirks."""

from __future__ import annotations

import datetime

from lapcare.core.battery_analysis import (
    HealthClass,
    classify_wear,
    snapshot_from_wear,
    wear_percent,
)
from lapcare.core.models import BatteryWear, CapacityUnit


def test_wear_matches_manual_e16_math() -> None:
    # M2 acceptance criterion: E16 Gen 2 real values.
    wear = wear_percent(54_290_000, 57_000_000)
    assert wear is not None
    assert round(wear, 2) == 4.75


def test_wear_unknowable_is_none() -> None:
    assert wear_percent(None, 57_000_000) is None
    assert wear_percent(54_290_000, None) is None
    assert wear_percent(54_290_000, 0) is None


def test_full_above_design_clamps_to_zero() -> None:
    # Fresh/recalibrated packs report full > design (pathological fixture).
    assert wear_percent(60_000_000, 57_000_000) == 0.0


def test_classification_thresholds() -> None:
    assert classify_wear(None) is HealthClass.UNKNOWN
    assert classify_wear(0.0) is HealthClass.GOOD
    assert classify_wear(14.99) is HealthClass.GOOD
    assert classify_wear(15.0) is HealthClass.FAIR
    assert classify_wear(29.99) is HealthClass.FAIR
    assert classify_wear(30.0) is HealthClass.POOR


def test_snapshot_from_wear() -> None:
    wear = BatteryWear(
        name="BAT0",
        capacity_full=54_290_000,
        capacity_design=57_000_000,
        capacity_unit=CapacityUnit.MICRO_WATT_HOURS,
        cycle_count=92,
    )
    snap = snapshot_from_wear(wear, day=datetime.date(2026, 7, 7))
    assert snap.day == "2026-07-07"
    assert snap.battery_name == "BAT0"
    assert snap.cycle_count == 92
    assert snap.wear_percent is not None
    assert round(snap.wear_percent, 2) == 4.75
