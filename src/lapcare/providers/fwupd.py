# SPDX-License-Identifier: GPL-3.0-or-later
"""fwupd provider: firmware devices/releases/updates via libfwupd (ADR-0009).

Implements core.ports.FirmwareProvider. Concrete class FwupdGir.

Transport (ADR-0009): ``gi.repository.Fwupd`` (``Fwupd.Client``), the same
GObject-Introspection library ``fwupdmgr``/GNOME Software use — not raw
``Gio.DBusConnection`` calls to ``org.freedesktop.fwupd``. fwupd owns
download, Jcat/GPG signature verification, and the Unix-fd handoff for
``Install``; this provider never touches firmware bytes.

Protocol owned here (calls block; run off the main thread via Scheduler,
same as every other provider):
- ``Client.get_devices(None) -> [Fwupd.Device]``: one device row per
  ``Fwupd.Device``, e.g. "UEFI dbx", "ThinkPad EC", "System Firmware".
  ``Device.get_flags()``/``has_flag()``: ``UPDATABLE`` (can be offered an
  update at all), ``NEEDS_REBOOT`` (device-level, distinct from an
  update-triggered reboot). ``get_update_state()``: one of
  UNKNOWN/PENDING/SUCCESS/FAILED/FAILED_TRANSIENT/NEEDS_REBOOT (history of
  the *last* update on this device, not the current job).
- ``Client.get_upgrades(device_id, None) -> [Fwupd.Release]``: fwupd raises
  ``Fwupd.Error.NOTHING_TO_DO``/``NOT_FOUND`` when a device has no newer
  release — that is data (empty list), not ``ProviderUnavailable``.
- ``Client.get_remotes(None) -> [Fwupd.Remote]`` + ``Client.refresh_remote()``
  per enabled ``DOWNLOAD``-kind remote: "metadata refresh". Only remotes
  with ``RemoteFlags.ENABLED`` and ``RemoteKind.DOWNLOAD`` are refreshed —
  ``LOCAL``/``DIRECTORY`` remotes have no network metadata to fetch.
- ``battery_precondition()``: a raw synchronous ``Properties.GetAll`` on
  ``/`` — **not** ``Client.get_battery_level()``/``get_battery_threshold()``,
  which only populate via a *later* ``PropertiesChanged`` signal
  (`fwupd_client_connect_async`'s initial property sync deliberately
  excludes battery fields; confirmed against upstream
  `libfwupd/fwupd-client.c`, so a freshly built client always reads back the
  101 sentinel). fwupd's sentinel **101 means "unknown"** (desktops,
  AC-only systems, or the daemon not reporting it yet) — translated to
  ``None`` here so ``core.firmware_policy`` only ever sees the
  Optional-by-default convention.
- ``Client.install_release(device, release, install_flags, download_flags,
  None)``: blocking; fwupd does the whole download+verify+flash+(maybe)
  reboot-schedule flow. Run via ``asyncio.to_thread`` on a **dedicated**
  client: on the 26.04 native scheduler provider coroutines execute on the
  GTK main thread (ADR-0007), so the minutes-long flash must hop off it, and
  a separate client/context means it never contends with concurrent short
  reads. ``Fwupd.Error.AUTH_FAILED``/``PERMISSION_DENIED`` map to
  ``PrivilegedActionDenied`` (declined polkit — ADR-0004: quiet degradation,
  never a page error); every other fwupd error maps to
  ``FirmwareInstallFailed``.
- Every client gets a persistent private ``GLib.MainContext`` via
  ``set_main_context()`` — see ``_new_client`` for the crash this prevents.
- Change/progress notification: **raw ``Gio.DBusConnection`` signal
  subscriptions** on ``org.freedesktop.fwupd`` (``Changed``,
  ``Device{Added,Removed,Changed}``) and its ``PropertiesChanged``
  (``Percentage``/``Status``) — not ``Fwupd.Client``'s own GObject signals.
  Measured against the local dbusmock template: ``Fwupd.Client``'s device/
  property-notify signals only fire once ``connect_async()`` has built its
  internal proxy, which needs a GLib-callback bridge (the "second async
  idiom" ADR-0009 rejects) — and even then, ``install_release()`` blocks the
  calling thread, so property-notify signals fired *on that same thread*
  never reach a callback anyway. Raw signal subscriptions on the shared
  system-bus connection have neither problem: ``subscribe()`` (main-thread
  only, called once at page load — same convention as ``upower.py``) wires
  up both device-change and progress listeners once; ``install()`` (which
  runs on whatever thread the Scheduler uses, per ADR-0007) just points
  ``self._on_progress`` at the caller's callback for the duration of the
  call. The listener itself always runs via the main thread's main-context
  iteration, so it calls ``on_progress`` directly — no ``GLib.idle_add``
  needed. If nothing ever called ``subscribe()``, progress simply never
  fires (safe degradation, not a crash).

Quirk: the port passes releases by ``(device_id, version)``, never a
``Fwupd.Release`` GObject (``core/ports.py`` is stdlib-only) — ``install()``
re-resolves the live object via a fresh ``get_upgrades()`` call immediately
before installing.

Unavailability: no system bus or no fwupd name owner -> ProviderUnavailable
(TOOL_MISSING, tool="fwupd") — the case inside containers/CI (no fwupd
daemon) and on any non-UEFI/BIOS-unsupported machine without fwupd installed.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

import gi

gi.require_version("Fwupd", "2.0")
gi.require_version("Gio", "2.0")
from gi.repository import Fwupd, Gio, GLib

from lapcare.core.errors import (
    FirmwareInstallFailed,
    PrivilegedActionDenied,
    ProviderParseError,
    ProviderTimeout,
    ProviderUnavailable,
)
from lapcare.core.models import Availability, FirmwareDevice, FirmwareRelease, UpdateState
from lapcare.platform.dbus import system_bus

log = logging.getLogger(__name__)

SOURCE = "fwupd"
_BUS_NAME = "org.freedesktop.fwupd"
_CALL_TIMEOUT_MS = 5000
_UNKNOWN_BATTERY = 101  # fwupd's sentinel for "can't tell"

_UPDATE_STATE_MAP = {
    Fwupd.UpdateState.UNKNOWN: UpdateState.UNKNOWN,
    Fwupd.UpdateState.PENDING: UpdateState.PENDING,
    Fwupd.UpdateState.SUCCESS: UpdateState.SUCCESS,
    Fwupd.UpdateState.FAILED: UpdateState.FAILED,
    Fwupd.UpdateState.FAILED_TRANSIENT: UpdateState.FAILED_TRANSIENT,
    Fwupd.UpdateState.NEEDS_REBOOT: UpdateState.NEEDS_REBOOT,
}

_URGENCY_MAP = {
    Fwupd.ReleaseUrgency.CRITICAL: "critical",
    Fwupd.ReleaseUrgency.HIGH: "high",
    Fwupd.ReleaseUrgency.MEDIUM: "medium",
    Fwupd.ReleaseUrgency.LOW: "low",
}

_AUTH_ERROR_CODES = (Fwupd.Error.AUTH_FAILED, Fwupd.Error.PERMISSION_DENIED)

BusFactory = Callable[[], Gio.DBusConnection]


def _device_to_model(d: Fwupd.Device) -> FirmwareDevice:
    device_id = d.get_id()
    if not device_id:
        raise ProviderParseError(SOURCE, "device with no id")
    return FirmwareDevice(
        id=device_id,
        name=d.get_name(),
        summary=d.get_summary(),
        vendor=d.get_vendor(),
        version=d.get_version(),
        version_lowest=d.get_version_lowest(),
        updatable=d.has_flag(Fwupd.DeviceFlags.UPDATABLE),
        needs_reboot=d.has_flag(Fwupd.DeviceFlags.NEEDS_REBOOT),
        plugin=d.get_plugin(),
        update_state=_UPDATE_STATE_MAP.get(d.get_update_state(), UpdateState.UNKNOWN),
        update_error=d.get_update_error(),
    )


def _translate_install_error(device_id: str, exc: GLib.Error) -> Exception:
    """Split out for direct unit testing (constructed GLib.Error, no bus needed)."""
    if any(exc.matches(Fwupd.error_quark(), code) for code in _AUTH_ERROR_CODES):
        return PrivilegedActionDenied(f"{_BUS_NAME}.install")
    return FirmwareInstallFailed(device_id, exc.message)


def _release_to_model(r: Fwupd.Release) -> FirmwareRelease:
    version = r.get_version()
    if not version:
        raise ProviderParseError(SOURCE, "release with no version")
    size = r.get_size()
    return FirmwareRelease(
        version=version,
        name=r.get_name(),
        summary=r.get_summary(),
        description=r.get_description(),
        size=size or None,
        urgency=_URGENCY_MAP.get(r.get_urgency()),
    )


def _new_client() -> Fwupd.Client:
    # why: without set_main_context, every libfwupd sync helper creates and
    # then FREES a fresh GMainContext, leaving the client's internal
    # GDBusProxy bound to freed memory — the next daemon signal (or the name
    # owner changing) dispatches into it and crashes whatever GLib main loop
    # runs next (measured; fwupd-client-sync.c fwupd_client_helper_free).
    # A persistent private context is the upstream-sanctioned fix.
    client = Fwupd.Client.new()
    client.set_main_context(GLib.MainContext.new())
    return client


class FwupdGir:
    def __init__(
        self, client: Fwupd.Client | None = None, bus_factory: BusFactory = system_bus
    ) -> None:
        self._client = client or _new_client()
        self._bus_factory = bus_factory
        self._bus: Gio.DBusConnection | None = None
        self._on_progress: Callable[[int | None, str], None] | None = None

    def _connection(self) -> Gio.DBusConnection:
        # why: PyGObject ties signal_subscribe callbacks to this wrapper's
        # lifetime — the provider must hold a strong reference or its
        # subscriptions die silently once the local goes out of scope
        # (measured against the dbusmock template; upower.py relies on the
        # same instance-level caching).
        if self._bus is None:
            try:
                self._bus = self._bus_factory()
            except GLib.Error as exc:
                raise ProviderUnavailable(SOURCE, Availability.TOOL_MISSING, tool="fwupd") from exc
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

    async def list_devices(self) -> list[FirmwareDevice]:
        try:
            devices = self._client.get_devices(None)
        except GLib.Error as exc:
            raise ProviderUnavailable(SOURCE, Availability.TOOL_MISSING, tool="fwupd") from exc
        return sorted((_device_to_model(d) for d in devices), key=lambda d: d.name or d.id)

    async def list_upgrades(self, device_id: str) -> list[FirmwareRelease]:
        try:
            releases = self._client.get_upgrades(device_id, None)
        except GLib.Error as exc:
            if exc.matches(Fwupd.error_quark(), Fwupd.Error.NOTHING_TO_DO) or exc.matches(
                Fwupd.error_quark(), Fwupd.Error.NOT_FOUND
            ):
                return []  # no newer release — data, not unavailability
            raise ProviderUnavailable(SOURCE, Availability.TOOL_MISSING, tool="fwupd") from exc
        return [_release_to_model(r) for r in releases]

    async def refresh_metadata(self) -> None:
        try:
            remotes = self._client.get_remotes(None)
        except GLib.Error as exc:
            raise ProviderUnavailable(SOURCE, Availability.TOOL_MISSING, tool="fwupd") from exc

        targets = [
            r
            for r in remotes
            if r.get_kind() == Fwupd.RemoteKind.DOWNLOAD and r.has_flag(Fwupd.RemoteFlags.ENABLED)
        ]
        failures: list[str] = []
        for remote in targets:
            try:
                self._client.refresh_remote(remote, Fwupd.ClientDownloadFlags.NONE, None)
            except GLib.Error as exc:
                log.debug("remote %s refresh failed: %s", remote.get_id(), exc.message)
                failures.append(remote.get_id() or "?")
        if targets and len(failures) == len(targets):
            raise ProviderTimeout(SOURCE, f"all remotes unreachable: {', '.join(failures)}")

    def battery_precondition(self) -> tuple[int | None, int | None]:
        # Raw GetAll, not Fwupd.Client.get_battery_level()/_threshold(): those
        # only populate via a later PropertiesChanged signal (confirmed
        # against fwupd_client_connect_async's source — its initial property
        # sync deliberately excludes battery fields), so a freshly built
        # client would always read the 101 "unknown" sentinel.
        try:
            (props,) = (
                self._connection()
                .call_sync(
                    _BUS_NAME,
                    "/",
                    "org.freedesktop.DBus.Properties",
                    "GetAll",
                    GLib.Variant("(s)", (_BUS_NAME,)),
                    GLib.VariantType("(a{sv})"),
                    Gio.DBusCallFlags.NONE,
                    _CALL_TIMEOUT_MS,
                    None,
                )
                .unpack()
            )
        except (GLib.Error, ProviderUnavailable):
            return (None, None)
        level = props.get("BatteryLevel")
        threshold = props.get("BatteryThreshold")
        return (
            level if level is not None and level < _UNKNOWN_BATTERY else None,
            threshold if threshold is not None and threshold < _UNKNOWN_BATTERY else None,
        )

    async def install(
        self,
        device_id: str,
        release_version: str,
        on_progress: Callable[[int | None, str], None],
    ) -> None:
        try:
            device = self._client.get_device_by_id(device_id, None)
            upgrades = self._client.get_upgrades(device_id, None)
            release = next((r for r in upgrades if r.get_version() == release_version), None)
        except GLib.Error as exc:
            raise ProviderUnavailable(SOURCE, Availability.TOOL_MISSING, tool="fwupd") from exc
        if release is None:
            raise FirmwareInstallFailed(device_id, f"release {release_version} no longer offered")

        # why: a dedicated client so the minutes-long install never contends
        # with concurrent short reads for the shared client's context, and
        # asyncio.to_thread because on the 26.04 native scheduler provider
        # coroutines run ON the GTK main thread (ADR-0007) — a blocking flash
        # there would freeze the UI for its whole duration.
        install_client = _new_client()
        self._on_progress = on_progress
        try:
            await asyncio.to_thread(
                install_client.install_release,
                device,
                release,
                Fwupd.InstallFlags.NONE,
                Fwupd.ClientDownloadFlags.NONE,
                None,
            )
        except GLib.Error as exc:
            raise _translate_install_error(device_id, exc) from exc
        finally:
            self._on_progress = None

    def subscribe(self, on_change: Callable[[], None]) -> None:
        """Main-thread only (see platform.dbus threading note). Wires up both
        device-change notifications and progress delivery for install()."""
        bus = self._connection()

        def _changed(*_args: object) -> None:
            on_change()

        for member in ("Changed", "DeviceAdded", "DeviceRemoved", "DeviceChanged"):
            bus.signal_subscribe(
                _BUS_NAME, _BUS_NAME, member, "/", None, Gio.DBusSignalFlags.NONE, _changed
            )

        def _properties_changed(
            _connection: Gio.DBusConnection,
            _sender: str,
            _path: str,
            _iface: str,
            _signal: str,
            params: GLib.Variant,
        ) -> None:
            if self._on_progress is None:
                return
            _changed_iface, changed, _invalidated = params.unpack()
            if "Percentage" not in changed and "Status" not in changed:
                return
            pct = changed.get("Percentage") or None  # 0 = unknown per fwupd's D-Bus doc
            status = changed.get("Status")
            status_nick = Fwupd.Status(status).value_nick if status is not None else ""
            self._on_progress(pct, status_nick)

        bus.signal_subscribe(
            _BUS_NAME,
            "org.freedesktop.DBus.Properties",
            "PropertiesChanged",
            "/",
            None,
            Gio.DBusSignalFlags.NONE,
            _properties_changed,
        )
        log.debug("subscribed to fwupd change/progress signals")
