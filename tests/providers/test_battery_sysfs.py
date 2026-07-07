# SPDX-License-Identifier: GPL-3.0-or-later
"""battery_sysfs against the real E16 capture and the synthetic quirk fixtures."""

from __future__ import annotations

from pathlib import Path

from lapcare.core.battery_analysis import wear_percent
from lapcare.core.models import Availability, CapacityUnit
from lapcare.providers.battery_sysfs import BatterySysfs

from .conftest import fixture_root


async def test_e16_gen2_real_capture() -> None:
    provider = BatterySysfs(root=fixture_root("battery_sysfs", "thinkpad-e16-gen2"))
    assert provider.availability() is Availability.OK

    batteries = await provider.list_batteries()
    assert len(batteries) == 1  # AC and (on the live machine) USB-C filtered out
    bat = batteries[0]
    assert bat.name == "BAT0"
    assert bat.capacity_unit is CapacityUnit.MICRO_WATT_HOURS
    assert bat.capacity_full == 54_290_000
    assert bat.capacity_design == 57_000_000
    assert bat.cycle_count == 92
    assert bat.manufacturer == "Sunwoda"
    assert bat.model_name == "L23D3PG2"
    wear = wear_percent(bat.capacity_full, bat.capacity_design)
    assert wear is not None and round(wear, 2) == 4.75


async def test_charge_unit_family() -> None:
    provider = BatterySysfs(root=fixture_root("battery_sysfs", "synthetic-charge-units"))
    (bat,) = await provider.list_batteries()
    assert bat.capacity_unit is CapacityUnit.MICRO_AMP_HOURS
    assert bat.capacity_full == 4_200_000
    assert bat.capacity_design == 5_000_000
    assert bat.cycle_count == 350


async def test_pathological_dual_battery() -> None:
    provider = BatterySysfs(root=fixture_root("battery_sysfs", "synthetic-pathological"))
    batteries = await provider.list_batteries()
    assert [b.name for b in batteries] == ["BAT0", "BAT1"]  # USB entry filtered

    bat0, bat1 = batteries
    # full above design: provider reports raw values; analysis clamps.
    assert bat0.capacity_full == 60_000_000
    assert wear_percent(bat0.capacity_full, bat0.capacity_design) == 0.0
    # cycle_count -1 normalized to None.
    assert bat1.cycle_count is None


async def test_no_power_supply_dir(tmp_path: Path) -> None:
    provider = BatterySysfs(root=tmp_path)
    assert provider.availability() is Availability.UNSUPPORTED_HARDWARE
    assert await provider.list_batteries() == []
