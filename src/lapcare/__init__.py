# SPDX-License-Identifier: GPL-3.0-or-later
"""Lapcare: battery health, firmware updates and diagnostics for ThinkPads on Linux.

This module must stay import-cheap: every entry point (launcher, -m, tests)
imports it before anything else, and mark_launch() anchors the ROADMAP M5
launch-time budget (< 1.5 s to window + first dashboard content).
"""

import os
import time

__version__ = "0.5.0"

APP_ID = "io.github.abhilashmuraleedharan.lapcare"

_T0_ENV = "LAPCARE_T0_MONOTONIC_NS"


def mark_launch() -> None:
    """Record process launch time; first caller wins (entry points call this
    before heavy imports). Environment-carried so exec'd children agree."""
    os.environ.setdefault(_T0_ENV, str(time.monotonic_ns()))


def launch_elapsed_s() -> float | None:
    """Seconds since mark_launch(), or None outside an entry point."""
    t0 = os.environ.get(_T0_ENV)
    if t0 is None:
        return None
    return (time.monotonic_ns() - int(t0)) / 1e9


mark_launch()
