# SPDX-License-Identifier: GPL-3.0-or-later
"""Firmware update preconditions — battery/threshold logic only."""

from __future__ import annotations

from lapcare.core.firmware_policy import battery_ok_for_update


def test_unknown_battery_level_is_ok() -> None:
    # 101 is fwupd's "unknown" sentinel (desktops, AC-only systems).
    assert battery_ok_for_update(None, 30) is True
    assert battery_ok_for_update(101, 30) is True


def test_no_threshold_is_no_constraint() -> None:
    assert battery_ok_for_update(5, None) is True


def test_at_or_above_threshold_is_ok() -> None:
    assert battery_ok_for_update(30, 30) is True
    assert battery_ok_for_update(31, 30) is True


def test_below_threshold_blocks() -> None:
    assert battery_ok_for_update(29, 30) is False
