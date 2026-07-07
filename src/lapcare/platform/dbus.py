# SPDX-License-Identifier: GPL-3.0-or-later
"""D-Bus plumbing: bus acquisition (GDBus via GLib).

This module owns HOW to reach a bus; each provider owns its protocol
(interfaces, paths, variants). ``Gio.bus_get_sync`` honors
``DBUS_SYSTEM_BUS_ADDRESS``, which is how python-dbusmock tests inject a
private bus.

Threading note (ADR-0007): synchronous GDBus calls are used inside provider
coroutines — on the 24.04 fallback they run on the background loop thread;
on 26.04 they run on the GLib main loop, where local-daemon property reads
are sub-millisecond. Signal subscriptions must be made from the GTK main
thread (they deliver via the thread-default main context at subscription
time) — that is why BatteryStatusProvider.subscribe() is a synchronous,
main-thread call.
"""

from __future__ import annotations

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio


def system_bus() -> Gio.DBusConnection:
    """Connect to the system bus. Raises GLib.Error when unreachable
    (e.g. inside containers without a system bus) — callers translate."""
    return Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
