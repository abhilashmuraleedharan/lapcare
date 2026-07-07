# SPDX-License-Identifier: GPL-3.0-or-later
"""upower provider: live battery status via org.freedesktop.UPower (D-Bus).

Implements core.ports.BatteryStatusProvider. Concrete class UPowerDbus.

Protocol owned here:
- Manager ``/org/freedesktop/UPower``: ``EnumerateDevices() -> ao``,
  ``DeviceAdded``/``DeviceRemoved`` signals.
- Per device ``org.freedesktop.UPower.Device`` properties: Type (2 =
  battery), PowerSupply (excludes wireless mice/keyboards), NativePath
  ("BAT0"), State, Percentage, TimeToEmpty/TimeToFull (seconds; 0 =
  unknown -> None), EnergyRate (W).
- State map: 1 charging, 2 discharging, 3 empty, 4 fully-charged,
  5/6 pending-(dis)charge -> NOT_CHARGING (what threshold-managed
  ThinkPads show), else UNKNOWN.

Change notification: one signal_subscribe on the Properties interface under
the UPower path namespace plus manager DeviceAdded/DeviceRemoved — coalesced
into the port's ``on_change`` callback (delivered on the GTK main thread;
subscribe() must be called from it).

Unavailability: no system bus or no UPower name -> ProviderUnavailable
(TOOL_MISSING, tool="upower") — the case inside containers/CI.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

from lapcare.core.errors import ProviderParseError, ProviderTimeout, ProviderUnavailable
from lapcare.core.models import Availability, BatteryState, BatteryStatus
from lapcare.platform.dbus import system_bus

log = logging.getLogger(__name__)

SOURCE = "upower"
_BUS_NAME = "org.freedesktop.UPower"
_MANAGER_PATH = "/org/freedesktop/UPower"
_DEVICE_IFACE = "org.freedesktop.UPower.Device"
_CALL_TIMEOUT_MS = 5000

_STATE_MAP = {
    1: BatteryState.CHARGING,
    2: BatteryState.DISCHARGING,
    3: BatteryState.EMPTY,
    4: BatteryState.FULL,
    5: BatteryState.NOT_CHARGING,
    6: BatteryState.NOT_CHARGING,
}

BusFactory = Callable[[], Gio.DBusConnection]


class UPowerDbus:
    def __init__(self, bus_factory: BusFactory = system_bus) -> None:
        self._bus_factory = bus_factory
        self._bus: Gio.DBusConnection | None = None

    def _connection(self) -> Gio.DBusConnection:
        if self._bus is None:
            try:
                self._bus = self._bus_factory()
            except GLib.Error as exc:
                raise ProviderUnavailable(SOURCE, Availability.TOOL_MISSING, tool="upower") from exc
        return self._bus

    def availability(self) -> Availability:
        try:
            bus = self._connection()
            has_owner = bus.call_sync(
                "org.freedesktop.DBus",
                "/org/freedesktop/DBus",
                "org.freedesktop.DBus",
                "NameHasOwner",
                GLib.Variant("(s)", (_BUS_NAME,)),
                GLib.VariantType("(b)"),
                Gio.DBusCallFlags.NONE,
                _CALL_TIMEOUT_MS,
                None,
            ).unpack()[0]
        except (GLib.Error, ProviderUnavailable):
            return Availability.TOOL_MISSING
        return Availability.OK if has_owner else Availability.TOOL_MISSING

    def _call(
        self, path: str, iface: str, method: str, args: GLib.Variant | None
    ) -> tuple[Any, ...]:  # why: GVariant.unpack() is dynamically shaped by design
        try:
            result = self._connection().call_sync(
                _BUS_NAME,
                path,
                iface,
                method,
                args,
                None,
                Gio.DBusCallFlags.NONE,
                _CALL_TIMEOUT_MS,
                None,
            )
        except GLib.Error as exc:
            if "Timeout" in (exc.message or ""):
                raise ProviderTimeout(SOURCE, exc.message) from exc
            raise ProviderUnavailable(SOURCE, Availability.TOOL_MISSING, tool="upower") from exc
        unpacked: tuple[Any, ...] = result.unpack()
        return unpacked

    async def read_status(self) -> list[BatteryStatus]:
        (device_paths,) = self._call(
            _MANAGER_PATH, "org.freedesktop.UPower", "EnumerateDevices", None
        )
        batteries: list[BatteryStatus] = []
        for path in device_paths:
            (props,) = self._call(
                path,
                "org.freedesktop.DBus.Properties",
                "GetAll",
                GLib.Variant("(s)", (_DEVICE_IFACE,)),
            )
            try:
                if props.get("Type") != 2 or not props.get("PowerSupply", False):
                    continue
                native = props.get("NativePath") or path.rsplit("/", 1)[-1]
                time_to_empty = int(props.get("TimeToEmpty", 0)) or None
                time_to_full = int(props.get("TimeToFull", 0)) or None
                batteries.append(
                    BatteryStatus(
                        name=str(native),
                        state=_STATE_MAP.get(int(props.get("State", 0)), BatteryState.UNKNOWN),
                        percentage=float(props["Percentage"]) if "Percentage" in props else None,
                        time_to_empty_s=time_to_empty,
                        time_to_full_s=time_to_full,
                        energy_rate_w=float(props["EnergyRate"]) if "EnergyRate" in props else None,
                    )
                )
            except (TypeError, ValueError, KeyError) as exc:
                log.debug("unparseable device %s: %s", path, exc)
                raise ProviderParseError(SOURCE, f"device {path}: {exc}") from exc
        batteries.sort(key=lambda b: b.name)
        return batteries

    def subscribe(self, on_change: Callable[[], None]) -> None:
        """Main-thread only (see platform.dbus threading note)."""
        bus = self._connection()

        def _changed(*_args: object) -> None:
            on_change()

        bus.signal_subscribe(
            _BUS_NAME,
            "org.freedesktop.DBus.Properties",
            "PropertiesChanged",
            None,
            None,
            Gio.DBusSignalFlags.NONE,
            _changed,
        )
        for member in ("DeviceAdded", "DeviceRemoved"):
            bus.signal_subscribe(
                _BUS_NAME,
                "org.freedesktop.UPower",
                member,
                _MANAGER_PATH,
                None,
                Gio.DBusSignalFlags.NONE,
                _changed,
            )
        log.debug("subscribed to UPower change signals")
