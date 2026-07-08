# SPDX-License-Identifier: GPL-3.0-or-later
"""Firmware update preconditions. Pure functions.

fwupd refuses installs below its own configured battery threshold, but the
UX acceptance criterion (ROADMAP M3) is to surface that *before* the user
commits, not just relay fwupd's eventual refusal. This is the one piece of
real domain logic in the firmware flow; everything else (device/release
listing, install orchestration) is I/O the fwupd provider owns.
"""

from __future__ import annotations

_UNKNOWN_BATTERY_LEVEL = 101  # Fwupd.Client.get_battery_level() sentinel


def battery_ok_for_update(battery_level: int | None, threshold: int | None) -> bool:
    """Whether battery charge is high enough to safely start an install.

    ``battery_level``: percentage 0-100, or None/101 when fwupd can't read it
    (desktops, AC-only systems, or the daemon not reporting it) — treated as
    OK since there's nothing to block on. ``threshold``: fwupd's configured
    minimum, or None if unset (no constraint).
    """
    if battery_level is None or battery_level >= _UNKNOWN_BATTERY_LEVEL:
        return True
    if threshold is None:
        return True
    return battery_level >= threshold
