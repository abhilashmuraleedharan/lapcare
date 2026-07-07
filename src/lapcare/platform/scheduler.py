# SPDX-License-Identifier: GPL-3.0-or-later
"""Async scheduler: the one sanctioned way to run provider I/O (ADR-0007).

Two implementations behind one interface, selected at startup by
create_scheduler():

- GLibEventLoopScheduler (PyGObject >= 3.50, Ubuntu 26.04+): asyncio runs on
  the GLib main loop via gi.events; coroutines and callbacks execute on the
  GTK main thread with no extra threads.
- ThreadLoopScheduler (PyGObject < 3.50, Ubuntu 24.04): one dedicated
  background thread runs a plain asyncio loop; completion callbacks are
  marshaled back to the GTK main thread via GLib.idle_add. This thread is the
  ONLY sanctioned thread in the process (constitution invariant).

Callers (view-models) never touch asyncio primitives directly: they submit a
coroutine and receive on_success/on_error on the GTK main thread. When Ubuntu
24.04 leaves the support matrix, ThreadLoopScheduler is deleted and no caller
changes.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable, Coroutine
from typing import Any, Protocol, TypeVar

from gi.repository import GLib

log = logging.getLogger(__name__)

T = TypeVar("T")


class Scheduler(Protocol):
    """What the composition root hands to view-models."""

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def submit(
        self,
        coro: Coroutine[Any, Any, T],
        on_success: Callable[[T], None],
        on_error: Callable[[BaseException], None],
    ) -> None:
        """Run ``coro``; deliver exactly one callback on the GTK main thread."""
        ...


class GLibEventLoopScheduler:
    """Native integration: asyncio on the GLib main loop (gi.events)."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self) -> None:
        import gi.events

        policy = gi.events.GLibEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
        self._loop = policy.get_event_loop()
        log.info("scheduler=native (gi.events on GLib main loop)")

    def stop(self) -> None:
        # The loop belongs to the GLib main context, which the application
        # owns; nothing to tear down here.
        self._loop = None

    def submit(
        self,
        coro: Coroutine[Any, Any, T],
        on_success: Callable[[T], None],
        on_error: Callable[[BaseException], None],
    ) -> None:
        if self._loop is None:
            raise RuntimeError("scheduler not started")
        task = self._loop.create_task(coro)

        def _done(t: asyncio.Task[T]) -> None:
            # Already on the GTK main thread: the loop IS the main context.
            exc = t.exception()
            if exc is not None:
                on_error(exc)
            else:
                on_success(t.result())

        task.add_done_callback(_done)


class ThreadLoopScheduler:
    """Fallback: dedicated background asyncio loop thread + GLib.idle_add."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="lapcare-async-loop", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=5):
            raise RuntimeError("async loop thread failed to start")
        log.info("scheduler=thread-loop fallback (PyGObject < 3.50, ADR-0007)")

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._ready.set()
        try:
            loop.run_forever()
        finally:
            loop.close()

    def stop(self) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None
        self._loop = None
        self._ready.clear()

    def submit(
        self,
        coro: Coroutine[Any, Any, T],
        on_success: Callable[[T], None],
        on_error: Callable[[BaseException], None],
    ) -> None:
        if self._loop is None:
            raise RuntimeError("scheduler not started")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        def _dispatch(f: Any) -> None:
            # Runs on the loop thread; hop to the GTK main thread.
            def _deliver() -> bool:
                exc = f.exception()
                if exc is not None:
                    on_error(exc)
                else:
                    on_success(f.result())
                return False  # GLib.SOURCE_REMOVE

            GLib.idle_add(_deliver)

        future.add_done_callback(_dispatch)


def has_native_integration() -> bool:
    try:
        import gi.events  # noqa: F401
    except ImportError:
        return False
    return True


def create_scheduler() -> Scheduler:
    """Pick the mechanism for this system (ADR-0007). Called by app.main."""
    if has_native_integration():
        return GLibEventLoopScheduler()
    return ThreadLoopScheduler()
