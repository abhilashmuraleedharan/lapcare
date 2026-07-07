# SPDX-License-Identifier: GPL-3.0-or-later
"""Scheduler tests: both ADR-0007 mechanisms, driven from a GLib main loop.

The native (gi.events) tests skip automatically where PyGObject < 3.50 — CI's
full lane runs both LTS containers, so both paths are exercised in CI.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from gi.repository import GLib

from lapcare.core.ports import Scheduler
from lapcare.platform import scheduler as sched_mod
from lapcare.platform.scheduler import (
    GLibEventLoopScheduler,
    ThreadLoopScheduler,
    create_scheduler,
    has_native_integration,
)


async def _answer() -> int:
    await asyncio.sleep(0.01)
    return 42


async def _boom() -> int:
    await asyncio.sleep(0.01)
    raise ValueError("boom")


def _drive(scheduler: Scheduler, coro: Any) -> dict[str, Any]:
    """Submit coro, run a GLib main loop until a callback lands, return it."""
    outcome: dict[str, Any] = {}
    loop = GLib.MainLoop()

    def on_success(value: Any) -> None:
        outcome["value"] = value
        loop.quit()

    def on_error(exc: BaseException) -> None:
        outcome["error"] = exc
        loop.quit()

    def timeout() -> bool:
        outcome["timeout"] = True
        loop.quit()
        return False

    scheduler.submit(coro, on_success, on_error)
    GLib.timeout_add_seconds(5, timeout)
    loop.run()
    assert "timeout" not in outcome, "callback never delivered"
    return outcome


def test_thread_loop_success() -> None:
    s = ThreadLoopScheduler()
    s.start()
    try:
        assert _drive(s, _answer())["value"] == 42
    finally:
        s.stop()


def test_thread_loop_error() -> None:
    s = ThreadLoopScheduler()
    s.start()
    try:
        err = _drive(s, _boom())["error"]
        assert isinstance(err, ValueError)
    finally:
        s.stop()


def test_thread_loop_not_started() -> None:
    with pytest.raises(RuntimeError):
        ThreadLoopScheduler().submit(_answer(), lambda v: None, lambda e: None)


@pytest.mark.skipif(not has_native_integration(), reason="PyGObject < 3.50: no gi.events")
def test_native_success() -> None:
    s = GLibEventLoopScheduler()
    s.start()
    try:
        assert _drive(s, _answer())["value"] == 42
    finally:
        s.stop()


@pytest.mark.skipif(not has_native_integration(), reason="PyGObject < 3.50: no gi.events")
def test_native_error() -> None:
    s = GLibEventLoopScheduler()
    s.start()
    try:
        err = _drive(s, _boom())["error"]
        assert isinstance(err, ValueError)
    finally:
        s.stop()


def test_factory_matches_environment() -> None:
    s = create_scheduler()
    expected = GLibEventLoopScheduler if has_native_integration() else ThreadLoopScheduler
    assert isinstance(s, expected)
    assert isinstance(s, sched_mod.GLibEventLoopScheduler | sched_mod.ThreadLoopScheduler)
