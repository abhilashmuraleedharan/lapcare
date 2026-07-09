# M4 — Storage Health, Diagnostics & Report Export: Status

**State:** IN PROGRESS. **Branch:** `feature/m4` (single milestone PR, rebase-merged at close).
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
- [ ] C6 `feat(ui): Diagnostics page + Dashboard health score` — one-click run (< 10 s),
      per-signal confidence, health score card on Dashboard labeled experimental,
      unmeasured signals are honest (SMART unmeasured until authorized).
- [ ] C7 `feat: report export (MD/HTML/JSON)` — redacted by default; identifiers only on
      explicit opt-in; `ReportWriter` in platform; export action on the Diagnostics page.
- [ ] C8 `docs: module docs + adding-a-diagnostic guide` — providers.md sections
      (storage_smart, hwmon, disk_usage), `docs/guides/adding-a-diagnostic.md` (promised by
      AGENTS.md routing table since M0), security-design.md pointer to ADR-0006.
- [ ] C9 `docs: close milestone M4; release v0.5.0`.

## Acceptance criteria (from ROADMAP)

- [ ] SMART data after one polkit prompt (`auth_admin_keep`; verified on the E16 Gen 2 from
      an installed .deb — maintainer action, same shape as M3's install deferral)
- [ ] Declining the prompt degrades gracefully (quiet toast; inventory + rest of app
      unaffected — ADR-0004)
- [ ] Diagnostics complete in < 10 s
- [ ] Helper negative/injection suite passes (ADR-0006 §18 list, verbatim)
- [ ] Health score on Dashboard with per-signal confidence, labeled experimental
- [ ] Report export in MD/HTML/JSON, redacted by default
- [ ] `./check` + smoke green both LTS; full lane green at close
- [ ] Tag `v0.5.0`; GitHub release; CHANGELOG; ROADMAP

## Known deferrals / notes

- The full pkexec→polkit→helper flow needs an installed .deb and an interactive auth agent
  — dev builds and CI degrade to TOOL_MISSING by design (ADR-0006 consequences). CI covers
  the helper directly (injection suite) and the provider via injected fake runner;
  the interactive flow is the maintainer's manual-matrix entry.

## Retrospective

(at close)
