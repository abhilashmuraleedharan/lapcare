# M3 — Firmware Updates (fwupd/LVFS): Status

**State:** IN PROGRESS. **Branch:** `feature/m3` (single milestone PR, rebase-merged).
**Objective (ROADMAP):** Firmware page — device list, versions, release notes, metadata
refresh, updates via fwupd D-Bus (its polkit governs), reboot-required and progress states.
**Close = tag `v0.4.0` and the BETA release.**

**Transport decision:** ADR-0009 — `Fwupd.Client` (GObject Introspection over libfwupd), not
raw `Gio.DBusConnection` calls. `python-dbusmock` ships no fwupd template (the M2
retrospective's assumption was wrong — confirmed against upstream at M3 start); tests use a
small local template built from `dbusmock`'s `SKELETON`.

## Commit plan

- [x] C1 `docs: open milestone M3` — status file, ADR-0009 (firmware transport).
- [ ] C2 `feat(core): firmware models, ports, errors` — `FirmwareDevice`/`FirmwareRelease`/
      `UpdateState` models, `core/firmware_policy.py` (pure: AC/battery precondition,
      update-state text mapping), `FirmwareProvider` port, `FirmwareInstallFailed` error.
- [ ] C3 `provider: fwupd (read-only)` — device list, upgrades/releases, remotes + metadata
      refresh via `Fwupd.Client`; local dbusmock template; fixture-free (live D-Bus state, not
      a filesystem capture — documented as a deviation in module docs).
- [ ] C4 `provider: fwupd install + progress` — `install()` with `on_progress` callback
      (`notify::percentage`/`notify::status` marshaled via `GLib.idle_add`), device/remote
      change signals; dbusmock-scriptable success/failure/needs-reboot paths.
- [ ] C5 `feat(ui): Firmware page` — device list, per-device update availability, refresh
      metadata action; four-state page pattern; per-device degradation (one device's failed
      `GetUpgrades` doesn't kill the page).
- [ ] C6 `feat(ui): update flow` — AC/battery precondition banner before commit, progress
      state, reboot-required banner, failure banner with retry, post-update release notes;
      polkit lock emblem on the Install control; declined auth degrades quietly (toast).
- [ ] C7 `docs: fwupd module doc + quirks`.
- [ ] C8 `docs: close milestone M3; release v0.4.0 (BETA)`.

## Acceptance criteria (from ROADMAP)

- [ ] Full update flow verified on real hardware against LVFS — **see deferral below**; the
      read-only surface (device list, available upgrades, refresh metadata) is validated
      against the E16 Gen 2's real fwupd where the host environment allows it, but the
      *install* path needs an interactive polkit GUI prompt no headless agent can drive.
- [ ] Failure paths render correctly (dbusmock-scripted: install failure, needs-reboot)
- [ ] Unambiguous reboot flow
- [ ] Failure recovery path (retry without restarting the whole page)
- [ ] AC/battery preconditions surfaced before commit
- [ ] Post-update "what changed" (release notes shown after a successful install)
- [ ] Declined auth is silent (quiet degradation, no error page — ADR-0004)
- [ ] `./check` + smoke green both LTS; full lane green at close (verified on tag)
- [ ] Tag `v0.4.0`; GitHub pre-release published (BETA); CHANGELOG; ROADMAP

## Known deferrals / notes

- **Real-hardware *install* validation is out of reach for an autonomous agent by design**:
  fwupd's own polkit policy requires an interactive human at a GUI auth prompt (ADR-0004) —
  the same boundary that makes the privilege model safe makes it impossible to script. The
  maintainer must manually verify at least one real install on the E16 Gen 2 before this
  milestone is truly production-trustworthy; until then, the D-Bus/UI plumbing is verified via
  dbusmock and the manual matrix entry stays open. Same deferral shape as M2's "real UPower
  bus" item.
- python-dbusmock has no fwupd template; a local one lives under `tests/dbusmock_templates/`.
- No fixture-corpus entry for `fwupd` — device/release data is live daemon state, not a
  filesystem tree; the local dbusmock template's scripted responses serve the role fixtures
  play for other providers.

## Retrospective

*(written at milestone close)*
