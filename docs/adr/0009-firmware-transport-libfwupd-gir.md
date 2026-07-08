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
(`Fwupd.Client.get_devices()` etc. block; they run off the GTK main thread via the Scheduler,
same as `upower.py`'s `call_sync`). The GLib-native async variants
(`get_devices_async`/`install_release_async`) are **not** used — mixing two different async
idioms (asyncio-via-Scheduler and GLib-callback-via-`_finish`) in one provider would violate
"provider/platform I/O is `async def`" without adding anything the Scheduler doesn't already
give us.

Progress (`notify::percentage`, `notify::status` on the `Fwupd.Client` instance) is forwarded
through an `on_progress` callback parameter on `FirmwareProvider.install()`, wrapped in
`GLib.idle_add` inside the provider before it reaches the callback — GObject signal emission
happens synchronously on whatever thread is running `install_release()` (the scheduler's
background thread on Ubuntu 24.04), so this is the same one-sanctioned-boundary pattern
ADR-0007 already establishes, applied to a callback instead of a coroutine's result.

`core/ports.py` stays stdlib-only: `FirmwareProvider.install()` takes and returns plain
`core.models` types (`FirmwareRelease.version`, a `str`), never a `Fwupd.Release` GObject. The
provider re-resolves the live `Fwupd.Release` object by re-querying `get_upgrades()` and
matching on version immediately before installing, rather than caching GObjects across the
port boundary.

## Consequences

- One new runtime dependency: `gir1.2-fwupd-2.0` (pulls `libfwupd2`/`libfwupd3`). Both
  supported LTS releases ship it; no PPA needed.
- Firmware download/verify/fd-passing code does not exist in this codebase — it is entirely
  `libfwupd`'s, keeping `docs/security-design.md`'s "Lapcare never downloads firmware" claim
  literally true and out of our threat model.
- python-dbusmock ships **no** fwupd template (checked against upstream
  `dbusmock/templates/` at M3 start — the M2 retrospective's assumption that it did was
  wrong). Tests use a small local template (`tests/dbusmock_templates/fwupd.py`, built from
  `dbusmock`'s `SKELETON` pattern) implementing the read-only surface
  (`GetDevices`/`GetUpgrades`/`GetReleases`/`GetRemotes`) plus a scriptable `Install` that
  can be told to succeed, fail, or require reboot — real LVFS downloads are never exercised
  in CI.
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
