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
- [ ] C3 `feat(core)+provider: storage models, port, storage_smart` — `StorageDevice` /
      `SmartHealth` models, `StorageProvider` port, unprivileged `/sys/block` inventory,
      `smartctl --json` parsing behind the helper via the audited runner (`pkexec` joins
      `ALLOWED_TOOLS`; 126/127 → `PrivilegedActionDenied`), serial redaction at the parse
      boundary (ADR-0006 §17). Fixtures captured from the real E16 Gen 2 NVMe.
- [ ] C4 `feat(ui): Storage page` — unprivileged inventory renders with zero prompts;
      "Read health" action carries the lock emblem; declined auth = quiet toast; per-device
      degradation.
- [ ] C5 `feat(core): diagnostics engine + checks` — pure-core engine and the five initial
      checks (battery wear, SMART, firmware currency, thermal sanity, disk space) +
      minimal `hwmon` (temps) and `disk_usage` providers to feed them.
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
