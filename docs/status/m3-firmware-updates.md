# M3 — Firmware Updates (fwupd/LVFS): Status

**State:** COMPLETE (v0.4.0 — BETA). **Branch:** `feature/m3` (single milestone PR, rebase-merged).
**Objective (ROADMAP):** Firmware page — device list, versions, release notes, metadata
refresh, updates via fwupd D-Bus (its polkit governs), reboot-required and progress states.
**Close = tag `v0.4.0` and the BETA release.**

**Transport decision:** ADR-0009 — `Fwupd.Client` (GObject Introspection over libfwupd), not
raw `Gio.DBusConnection` calls. `python-dbusmock` ships no fwupd template (the M2
retrospective's assumption was wrong — confirmed against upstream at M3 start); tests use a
small local template built from `dbusmock`'s `SKELETON`.

## Commit plan

- [x] C1 `docs: open milestone M3` — status file, ADR-0009 (firmware transport).
- [x] C2 `feat(core): firmware models, ports, errors` — `FirmwareDevice`/`FirmwareRelease`/
      `UpdateState` models, `core/firmware_policy.py` (pure battery precondition),
      `FirmwareProvider` port, `FirmwareInstallFailed` error.
- [x] C3+C4 `provider: fwupd via libfwupd` — landed as ONE commit (the install/progress
      mechanics were inseparable from the transport spike): device list, upgrades/releases,
      remotes + metadata refresh, `install()` with `on_progress`, change signals. Local
      dbusmock template; fixture-free (live D-Bus state, not a filesystem capture —
      documented as a deviation in module docs). Three findings that reshaped the design,
      all recorded in ADR-0009/module docstring: (1) `Fwupd.Client` sync helpers free their
      per-call `GMainContext`, leaving the internal proxy bound to freed memory — every
      client needs `set_main_context()` with a persistent context or the process crashes on
      the next daemon signal; (2) the client's GObject signals and battery getters only work
      after an async `connect_async()`, so change/progress/battery use raw GDBus
      subscriptions/`GetAll` instead; (3) `install_release()` runs via `asyncio.to_thread`
      on a dedicated client — on 26.04's native scheduler, coroutines execute on the GTK
      main thread, and a minutes-long flash there would freeze the UI. Test infrastructure:
      one session-wide private system bus (two `DBusTestCase` classes each starting/stopping
      their own bus leaves Gio's singleton connection dead — process abort).
- [x] C5+C6 `feat(ui): Firmware page + update flow` — landed as ONE commit (the page and
      the flow share one view-model): device list with per-device update availability and
      per-device degradation; metadata refresh action (failure = toast, never a page
      state); battery precondition surfaced BEFORE commit; progress via busy banner;
      reboot-required banner computed from fwupd update states; failure banner with retry;
      post-update "what changed"; lock emblem on Install; declined auth = quiet toast
      (ADR-0004). Also fixes a packaging gap: `core/firmware_policy.py` and
      `providers/fwupd.py` were missing from `src/meson.build` install lists (the .deb
      would have crashed at import). **Read-only surface validated on the real E16 Gen 2**
      (container + host system-bus mount, AppArmor unconfined for the probe): 20 devices
      mapped, real NOTHING_TO_DO→[] path hit, battery precondition (62%, 25%) read live.
- [x] C7 `docs: fwupd module doc + quirks` — providers.md fwupd section (8 quirks, all
      evidence-backed), adding-a-provider guide gains the D-Bus/GIR reference pointers.
- [x] C8 `docs: close milestone M3; release v0.4.0 (BETA)`.

## Acceptance criteria (from ROADMAP)

- [ ] Full update flow verified on real hardware against LVFS — **OPEN, see deferral
      below**: the read-only surface (device list, upgrades, battery precondition) IS
      validated against the E16 Gen 2's real fwupd daemon, but the *install* path needs an
      interactive polkit GUI prompt no headless agent can drive — maintainer action.
- [x] Failure paths render correctly (unit-tested VM states; real install-failure path
      exercised via libfwupd's own client-side release validation + constructed errors)
- [x] Unambiguous reboot flow (banner names each device awaiting restart; recomputed from
      fwupd update states on every reload)
- [x] Failure recovery path (retryable failure banner; page and cards survive)
- [x] AC/battery preconditions surfaced before commit (fwupd's own threshold, checked
      client-side first; real E16 values 62%/25% read live)
- [x] Post-update "what changed" (release name/version/summary after success)
- [x] Declined auth is silent (quiet toast, never an error page — ADR-0004)
- [x] `./check` + smoke green both LTS; full lane green at close (verified on tag)
- [x] Tag `v0.4.0`; GitHub pre-release published (BETA); CHANGELOG; ROADMAP

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

- **The library was the hard part, not the protocol.** ADR-0009's transport call
  (libfwupd over raw D-Bus) was right — download/verify/fd-passing stayed out of our
  codebase — but `Fwupd.Client` came with three landmines the plan never predicted:
  freed-per-call main contexts (process-crashing), signals/getters inert until an async
  connect, and sync calls that block whatever thread runs them (fatal for the UI on the
  26.04 native scheduler). Every one was found by tests or measured probes, not review.
- **The dbusmock template assumption from M2's retrospective was wrong** — verify upstream
  claims at milestone open, not at commit time. Writing our own template was cheap and
  caught the device-id format assertion (`fwupd_device_id_is_valid`).
- **Second D-Bus test class broke the suite in a way the first never could**: dbusmock's
  per-class private buses vs. Gio's process-wide singleton connection. One session-wide
  bus is now the house rule (tests/providers/conftest.py).
- **Real-hardware probes keep paying**: the E16 run exercised the NOTHING_TO_DO→[] path,
  version-less devices, duplicate names, and real battery thresholds — none of which the
  synthetic mock data would have prioritized.
- **For M4:** ADR-0006 (helper threat model) is the entry gate and must be written FIRST;
  the smart/nvme providers are subprocess-shaped (back to the audited-runner recipe), and
  the diagnostics engine is pure core — the M4 risk is the polkit helper, nothing else.
