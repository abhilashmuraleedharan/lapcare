# SPDX-License-Identifier: GPL-3.0-or-later
"""Provider-test helpers: fixture roots and the shared private system bus.

One private system bus for the WHOLE test process, not one per test class:
``Gio.bus_get_sync`` returns a process-wide singleton connection, so a
per-class bus (dbusmock's default — its ``tearDownClass`` stops every bus in
a registry shared across ALL DBusTestCase subclasses) leaves the second
D-Bus-using test class holding a connection to a dead daemon; GDBus then
aborts the whole process during main-context iteration. Test classes must
NOT call ``start_system_bus()`` themselves and must no-op ``tearDownClass``.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import dbusmock
import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def fixture_root(source: str, machine: str) -> Path:
    root = FIXTURES / source / machine
    assert root.is_dir(), f"missing fixture: {root}"
    return root


@pytest.fixture(scope="session", autouse=True)
def shared_private_system_bus() -> Iterator[None]:
    """Start the one private system bus before any provider test runs."""
    dbusmock.DBusTestCase.start_system_bus()
    yield
    dbusmock.DBusTestCase.tearDownClass()  # stops the bus at session end
