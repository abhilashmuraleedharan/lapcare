# SPDX-License-Identifier: GPL-3.0-or-later
"""hwmon provider against the E16 Gen 2 capture (bogus EC slots included)."""

from __future__ import annotations

from pathlib import Path

from lapcare.core.models import Availability
from lapcare.providers.hwmon import HwmonSysfs

from .conftest import fixture_root

E16 = fixture_root("hwmon", "thinkpad-e16-gen2")


def test_availability() -> None:
    assert HwmonSysfs(root=E16).availability() is Availability.OK


def test_availability_without_hwmon(tmp_path: Path) -> None:
    assert HwmonSysfs(root=tmp_path).availability() is Availability.UNSUPPORTED_HARDWARE


async def test_readings_include_bogus_slots_verbatim() -> None:
    readings = await HwmonSysfs(root=E16).list_temperatures()
    by_key = {(r.chip, r.label): r.celsius for r in readings}

    assert by_key[("thinkpad", "CPU")] == 49.0
    assert by_key[("thinkpad", "GPU")] == 47.0
    assert by_key[("acpitz", None)] == 49.0  # unlabeled is normal
    assert by_key[("nvme", "Composite")] == 41.85
    assert by_key[("coretemp", "Package id 0")] == 58.0
    assert by_key[("coretemp", "Core 8")] == 54.0  # non-contiguous slot 10

    # The EC's unpopulated slots come through verbatim (2 °C, 13 °C):
    # plausibility is the diagnostics engine's policy, not a parse decision.
    unlabeled_thinkpad = sorted(
        r.celsius for r in readings if r.chip == "thinkpad" and r.label is None
    )
    assert unlabeled_thinkpad == [2.0, 13.0]
    # temp8 (unreadable on the live machine, absent here) is skipped.
    assert len([r for r in readings if r.chip == "thinkpad"]) == 4


async def test_no_hwmon_is_empty_list(tmp_path: Path) -> None:
    assert await HwmonSysfs(root=tmp_path).list_temperatures() == []
