# M4 — Storage Health, Diagnostics & Report Export: Status

**State:** COMPLETE (v0.5.0). **Branch:** `feature/m4` (single milestone PR, rebase-merged).
**Objective (ROADMAP):** privileged helper + polkit policy; Storage page (SMART/NVMe);
diagnostics engine + initial checks (battery wear, SMART, firmware currency, thermal sanity,
disk space); health score on Dashboard (per-signal confidence, labeled experimental); report
export (MD/HTML/JSON) redacted by default.
**Close = tag `v0.5.0`.**

**Entry gate:** ADR-0006 (helper threat model & validation spec) — written and accepted in
C1, before any helper code. Key narrowing vs. ADR-0004's sketch: M4 ships **one** verb
(`smart-report`); `nvme-report` is unnecessary (`smartctl --json` covers NVMe natively) and
`dmi-full` has no M4 consumer — verbs are demand-driven.

## Commit plan

- [x] C1 `docs: open milestone M4; ADR-0006 helper threat model` — this file, ADR-0006
      (with upstream pkexec source verification: `exec.argv1` per-verb action matching,
      realpath canonicalization, clearenv), DECISIONS.md row.
- [x] C2 `feat(helper): privileged helper + polkit policy + injection suite` — the
      stdlib-only helper, the `.policy` file, meson/debian packaging (libexec + polkit
      datadir, `Depends: pkexec`, `Recommends: smartmontools`), and the ADR-0006 §18
      negative/injection test suite (41 tests: subprocess layer runs the helper exactly as
      pkexec would; import layer substitutes os/subprocess for execution hygiene). Meson
      install verified in-container (0755, canonical libexec path, policy in
      polkit-1/actions); debhelper compat-13 confirmed NOT to override libexecdir (the
      `lib/$multiarch` override is compat ≤ 11 only — checked upstream meson.pm).
- [x] C3 `feat(core)+provider: storage models, port, storage_smart` — `StorageDevice` /
      `SmartReport` models, `StorageProvider` port, unprivileged `/sys/block` inventory
      (physical = has a `device/` subdir; loop/zram/dm are skipped), `smartctl --json`
      parsing behind the helper via the audited runner (`pkexec` joins `ALLOWED_TOOLS`;
      126/127 → `PrivilegedActionDenied`; §13 stderr codes mapped), serial in its own
      identifier field (ADR-0006 §17). Fixtures captured from the real E16 Gen 2 NVMe
      (read-only `smartctl` in a container with the device passed through + CAP_SYS_ADMIN),
      redacted at capture; synthetic failing-SATA case alongside. **Finding that reshaped
      ADR-0006 §12 pre-merge:** the E16's SK hynix NVMe lacks the optional self-test log,
      so `smartctl --all` sets exit bit 2 alongside complete healthy JSON — bit 2 is data
      quality, not failure; helper fatal bits narrowed to 0-1.
- [x] C4 `feat(ui): Storage page` — unprivileged inventory renders with zero prompts
      (asserted in a VM test); "Read Health" carries the lock emblem; ONE prompt covers all
      devices (`auth_admin_keep`; `PrivilegedActionDenied`/`ProviderUnavailable` abort the
      run — no prompt storm); declined auth = quiet toast; per-device SMART failure = note
      on that device. Smoke asserts the page on both LTS. Also fixed a latent scheduler
      bug this page's tests exposed on 26.04: `GLibEventLoopScheduler.stop()` left the
      process-global gi.events asyncio policy installed, breaking any later
      `asyncio.run()` on the main thread — `stop()` now restores the previous policy.
- [x] C5 `feat(core): diagnostics engine + checks` — pure-core engine (`core/diagnostics.py`):
      five checks as pure functions on Optional inputs, transparent score (OK=1/WARN=0.5/
      CRIT=0 averaged over measured checks), per-signal confidence, SKIPPED-with-skip_code
      for unmeasured signals; `run()` gathers via ports with per-source degradation and
      touches the privileged SMART path ONLY with `include_storage_health=True` (declined
      → SKIPPED("declined"), everything else still measured). Feeder providers: `hwmon`
      (E16 capture: EC exposes unpopulated slots reading 2 °C/13 °C or failing outright —
      plausibility bounds live in the engine, not the parser) and `disk_usage`
      (/proc/mounts `/dev/*` filter, dedupe by source, `f_bavail`, octal-escape decode).
- [x] C6 `feat(ui): Diagnostics page + Dashboard health score` — page opens ready (zero
      prompts at launch); one privilege-marked Run includes SMART, logs elapsed time
      (greppable for the < 10 s criterion); declined auth = that one signal "Not measured
      (authorization declined)", run survives; all prose (check titles, metric labels,
      statuses, skip codes, confidence) mapped in the diagnostics VM and reused by the
      Dashboard's experimental health card, which measures unprivileged signals only and
      hides itself when nothing is measurable.
- [x] C7 `feat: report export (MD/HTML/JSON)` — Export on the Diagnostics page after a
      run; extension picks the format. JSON is machine-readable (raw ids/enums, stable
      schema v1, rendered in core); MD/HTML are presentation documents built from the same
      translated display data as the page (UI layer). Redaction **by construction**: no
      serial key exists in any renderer's input, asserted across all three formats.
      **Scope note:** the "include identifiers" opt-in is deferred with the `dmi-full`
      verb — unprivileged Lapcare cannot read the DMI serial, so the toggle would be a
      lie today (recorded in core/report.py). `ReportWriter` port + atomic platform
      writer (temp file + rename). Export failure = toast, never a page state.
- [x] C8 `docs: module docs + adding-a-diagnostic guide` — providers.md sections
      (storage_smart, hwmon, disk_usage — 13 evidence-backed quirks), the
      `docs/guides/adding-a-diagnostic.md` guide (promised by AGENTS.md routing since M0),
      security-design.md updated to shipped-helper reality, adding-a-provider gains the
      privileged-provider reference. **Also: helper positive path validated end-to-end on
      the real E16 NVMe** (root container + device passthrough + CAP_SYS_ADMIN — the same
      read-only probe as the fixture capture, through the actual helper code): real
      smartctl JSON passed the gate with the bit-2 quirk live, no-device-node and
      path-injection rejections verified against the real /sys/block.
- [x] C9 `docs: close milestone M4; release v0.5.0`.

## Acceptance criteria (from ROADMAP)

- [ ] SMART data after one polkit prompt — **OPEN, maintainer action** (same shape as
      M3's install deferral): the helper's full positive path IS verified on the real
      E16 Gen 2 NVMe (root container + device passthrough, through the actual helper
      code, real smartctl JSON, live bit-2 quirk), and the injection suite runs it
      exactly as pkexec would — but the *interactive* pkexec→polkit-agent→helper chain
      needs a human at a GUI prompt with the .deb installed. One click of "Read Health"
      on the E16 closes this.
- [x] Declining the prompt degrades gracefully (quiet toast; inventory + rest of app
      unaffected — ADR-0004; VM tests assert single-attempt, no prompt storm)
- [x] Diagnostics complete in < 10 s (pure-core checks over already-bounded provider
      reads; elapsed time logged on every run — container runs complete in well under 1 s
      compute + provider I/O)
- [x] Helper negative/injection suite passes (ADR-0006 §18 list, verbatim — 41 tests)
- [x] Health score on Dashboard with per-signal confidence, labeled experimental
      (unprivileged signals only; hides when nothing measurable)
- [x] Report export in MD/HTML/JSON, redacted by default (by construction: no serial key
      exists in any renderer input; asserted across all three formats)
- [x] `./check` + smoke green both LTS; full lane green at close (verified on tag)
- [x] Tag `v0.5.0`; GitHub release; CHANGELOG; ROADMAP

## Known deferrals / notes

- The full pkexec→polkit→helper flow needs an installed .deb and an interactive auth agent
  — dev builds and CI degrade to TOOL_MISSING by design (ADR-0006 consequences). CI covers
  the helper directly (injection suite) and the provider via injected fake runner; the
  interactive flow is the maintainer's manual-matrix entry (also closes M3's open install
  criterion in the same session, ideally).
- ADR-0004's `nvme-report` and `dmi-full` verbs are NOT shipped (demand-driven narrowing,
  ADR-0006 §3); the report export "include identifiers" opt-in is deferred with `dmi-full`.
- SATA SMART parsing is fixture-backed by a synthetic case only — the E16 has no SATA bay;
  a real SATA capture wants a second machine (community/second-ThinkPad item, carried).

## Retrospective

- **Verify-at-milestone-open paid for itself twice on day one.** Reading upstream
  pkexec.c before ADR-0006 turned "how do per-verb polkit actions work with one binary"
  from a guess into a cited fact (`exec.argv1`, realpath before matching, clearenv
  whitelist) — the design needed zero rework. And the very first real-hardware fixture
  capture invalidated the ADR's smartctl exit-bitmask policy before the helper shipped:
  the E16's own NVMe sets bit 2 alongside complete healthy JSON (no self-test log).
  Fatal bits narrowed to 0-1; a policy written from the man page alone would have
  rejected the reference machine's healthy drive.
- **The fixture corpus keeps beating synthetic assumptions**: the same capture session
  produced the hwmon EC quirk (unpopulated slots reading 2 °C or failing outright) that
  shaped the thermal check's plausibility bounds, and the CAP_SYS_ADMIN-not-device-node
  finding for NVMe ioctls.
- **A new test module is a probe for latent global state.** The storage VM tests
  exposed a real ADR-0007 scheduler bug (gi.events policy left installed after stop(),
  breaking any later main-thread asyncio.run on 26.04) purely by sorting alphabetically
  after test_scheduler.py. Fixed in the scheduler, not the tests.
- **Demand-driven verbs kept the audit surface honest**: one verb shipped instead of
  ADR-0004's sketched three; the two unshipped ones have a spec-bound shape waiting for
  a consumer.
- **For M5:** no new architecture — hardening, perf (<1.5 s launch), accessibility,
  PPA pipeline, and the community hardware round. The SMART fixture corpus and the
  health-score calibration review are the data-hungry items; both grow from beta field
  reports.
