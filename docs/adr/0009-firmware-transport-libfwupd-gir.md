# ADR-0009: Firmware transport — libfwupd via GObject Introspection, not raw D-Bus calls

- **Status:** Accepted
- **Date:** 2026-07-08
- **Deciders:** Lead Architect, from the M3 fwupd protocol spike

## Context

ARCHITECTURE.md's transport preference is "D-Bus > sysfs > CLI"; `providers/upower.py` set the
precedent of talking to `org.freedesktop.fwupd`'s sibling `org.freedesktop.UPower` via raw
`Gio.DBusConnection.call_sync`. The naive plan for M3 was to repeat that pattern against
`org.freedesktop.fwupd` directly (confirmed method/signal set: `GetDevices`, `GetUpgrades`,
`GetReleases`, `GetRemotes`, `Install`, `Changed`/`DeviceAdded`/`DeviceChanged`/
`DeviceRemoved` — see `src/org.freedesktop.fwupd.xml` upstream).

Two things break that plan on inspection:

1. **`Install(id, handle, options)` takes an already-open Unix file descriptor to a local
   `.cab` file** — fwupd does not download firmware itself over D-Bus. Something in the
   client has to fetch the release's URI, verify it landed, and hand over a real fd (with
   `Gio.UnixFDList` marshaling). Hand-rolling that against a security-critical firmware-write
   path is exactly the kind of custom protocol code the constitution's "wrap, don't
   reimplement" principle warns against, and `docs/security-design.md` already claims
   "Lapcare never downloads firmware" — a claim only true if something else owns the download.
2. Ubuntu ships **`gir1.2-fwupd-2.0`** (from `libfwupd2`/`libfwupd3`) on both 24.04
   (`2.0.20-1ubuntu2~24.04.1`) and 26.04 — the same official client library `fwupdmgr` and
   GNOME Software link against. `Fwupd.Client` wraps the exact D-Bus protocol above (it is
   not a CLI, not a reimplementation) and additionally owns: downloading a release's payload
   over HTTPS with Jcat/GPG signature verification (`install_release()`), constructing the fd
   passed to `Install`, and exposing `percentage`/`status` as GObject properties with
   `notify::` signals for progress — the exact shape our GLib-native code already consumes
   elsewhere (cf. `platform/dbus.py`, ADR-0007's `GLib.idle_add` marshaling).

## Decision

The `fwupd` provider (`providers/fwupd.py`) talks to fwupd through **`gi.repository.Fwupd`
(`Fwupd.Client`)**, not through raw `Gio.DBusConnection` calls. This is still "the D-Bus
tier" of the transport preference — `Fwupd.Client` is a thin GObject wrapper over the same
system-bus protocol, honors `DBUS_SYSTEM_BUS_ADDRESS` (so dbusmock injection keeps working
for the read-only surface: `GetDevices`/`GetUpgrades`/`GetReleases`/`GetRemotes`), and adds no
new privilege surface — it is the same code path `fwupdmgr` uses, so fwupd's own polkit
policy and LVFS signature verification govern every write exactly as ADR-0004 already commits
to.

`gir1.2-fwupd-2.0` is added to `tools/install-deps.sh` and `debian/control` as a new runtime
dependency (constitution invariant #7 requires this ADR for that).

Provider methods stay synchronous-inside-`async def`, matching every other provider
(`Fwupd.Client.get_devices()` etc. block, same as `upower.py`'s `call_sync` — fast local
calls, acceptable even on the 26.04 native scheduler where coroutines run on the GTK main
thread). The one *slow* call, `install_release()` (download + flash, minutes), runs via
`asyncio.to_thread` on a **dedicated client instance**: it must not block the GTK main thread
on 26.04, and a separate client/context means concurrent short reads never contend with it.
The GLib-native async variants (`get_devices_async`/`install_release_async`) are **not**
used — mixing two different async idioms (asyncio-via-Scheduler and
GLib-callback-via-`_finish`) in one provider would violate "provider/platform I/O is
`async def`" for no gain.

Change notification and install progress use **raw `Gio.DBusConnection` signal
subscriptions** (`Changed`/`Device{Added,Removed,Changed}` and `PropertiesChanged` for
`Percentage`/`Status`), not `Fwupd.Client`'s GObject signals: measured against the dbusmock
template, the client's own signals only fire after an async `connect_async()` proxy setup
(the second async idiom this ADR rejects), and progress notifications emitted on the thread
blocked inside `install_release()` could never reach a callback anyway. Likewise
`battery_precondition()` reads `BatteryLevel`/`BatteryThreshold` via a raw
`Properties.GetAll` — the client's cached getters only populate from a later
`PropertiesChanged`, so a fresh client always reads the 101 "unknown" sentinel. This hybrid
(libfwupd for everything involving download/verify/install semantics; raw GDBus for signals
and daemon properties) is deliberate, not drift.

`core/ports.py` stays stdlib-only: `FirmwareProvider.install()` takes and returns plain
`core.models` types (`FirmwareRelease.version`, a `str`), never a `Fwupd.Release` GObject. The
provider re-resolves the live `Fwupd.Release` object by re-querying `get_upgrades()` and
matching on version immediately before installing, rather than caching GObjects across the
port boundary.

## Consequences

- One new runtime dependency: `gir1.2-fwupd-2.0` (pulls `libfwupd2`/`libfwupd3`). Both
  supported LTS releases ship it; no PPA needed.
- **`Client.refresh_remote()` is itself a client-side network operation**, not a D-Bus call
  the daemon services: `fwupd_client_refresh_remote_async()` downloads the remote's signature
  and metadata directly (`fwupd_client_download_bytes_async`, the same in-process downloader
  `install_release()` uses for firmware) and only hands the verified result to the daemon via
  `UpdateMetadata` once both fetches succeed (confirmed against
  `libfwupd/fwupd-client.c` upstream). "Metadata refresh" therefore makes a real outbound
  HTTPS request from the Lapcare process, same trust boundary as a firmware download — worth
  knowing before assuming every network-touching operation in this feature is delegated to a
  system daemon. It is still libfwupd's downloader and verification code, not ours.
- Firmware download/verify/fd-passing code does not exist in this codebase — it is entirely
  `libfwupd`'s, keeping `docs/security-design.md`'s "Lapcare never downloads firmware" claim
  literally true and out of our threat model.
- **Every `Fwupd.Client` must get a persistent `GLib.MainContext` via `set_main_context()`
  immediately after construction.** Without one, each libfwupd *sync* helper creates and then
  frees a fresh context, leaving the client's internal `GDBusProxy` bound to freed memory —
  the next daemon signal or name-owner change dispatches into it and crashes whatever GLib
  main loop runs next (measured: reproducible process abort; root cause confirmed in upstream
  `fwupd-client-sync.c` `fwupd_client_helper_free`). `providers/fwupd.py:_new_client()` is
  the single sanctioned constructor.
- python-dbusmock ships **no** fwupd template (checked against upstream
  `dbusmock/templates/` at M3 start — the M2 retrospective's assumption that it did was
  wrong). Tests use a small local template (`tests/dbusmock_templates/fwupd.py`) implementing
  the read-only surface (`GetDevices`/`GetUpgrades`/`GetReleases`/`GetRemotes` plus
  convenience `AddDevice`/`AddUpgrade`/`AddRemote` methods). Install *failure* paths are
  covered without a mocked `Install`: libfwupd validates releases client-side before touching
  the network (a release with no URIs fails deterministically), and polkit-denial translation
  is unit-tested with constructed `GLib.Error`s. Real LVFS downloads are never exercised in
  CI.
- The actual firmware-write path (`install_release`, real HTTPS download, real polkit prompt,
  real reboot) cannot be exercised non-interactively at all — `pkexec`/polkit requires an
  interactive human at a GUI prompt by design (ADR-0004). It is validated manually on the
  E16 Gen 2 by the maintainer, same deferral shape as M2's "real UPower bus" item, tracked in
  `docs/status/m3-firmware-updates.md`.

## Alternatives Considered

- **Raw `Gio.DBusConnection` calls to `org.freedesktop.fwupd` (repeat the `upower.py`
  pattern):** rejected — would require Lapcare to implement HTTPS download, checksum
  verification, and `Gio.UnixFDList` fd-passing itself for `Install`, which is precisely the
  "reimplementation instead of wrapping" the constitution forbids for a security-sensitive
  write path, and contradicts the existing "Lapcare never downloads firmware" security claim.
- **Shell out to `fwupdmgr` via `platform/subprocess.py`:** rejected — sits below D-Bus in the
  transport preference for no reason here (the GIR library exists and is more precise:
  progress as GObject properties beats parsing `fwupdmgr`'s human-readable progress output);
  would also need `--json` text parsing for release notes/versions, one more translation layer
  than binding directly to the typed `Fwupd.Device`/`Fwupd.Release` objects.
- **`Fwupd.Client`'s GLib-native async methods (`*_async`/`*_finish`):** rejected — a second
  async idiom alongside the Scheduler's asyncio-based one buys nothing and complicates every
  call site; the Scheduler already gets provider I/O off the main thread.
