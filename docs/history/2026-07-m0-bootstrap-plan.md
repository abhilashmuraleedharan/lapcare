# LapCare — Repository Bootstrap & Milestone M0 Implementation Plan

**Author:** Lead Architect. **Date:** 2026-07-06.
**Basis:** Engineering Plan v1.1 (approved) + Review Reconciliation.
**Status:** Awaiting approval. Nothing has been created — no repo, no files. This document is
the executable plan.

---

# Part A — Repository Name & GitHub Metadata (recommendation)

| Item | Recommendation | Rationale |
|---|---|---|
| Repository name | **`lapcare`** | Matches the working codename in all approved docs; trademark-clean (no "ThinkPad"/"Lenovo"/"Vantage"); short, lowercase, packageable as-is (`lapcare.deb`, `lapcare` binary). If ADR-0001 later picks a different product name, a repo rename is cheap (GitHub redirects). |
| Description | *"Battery health, firmware updates and diagnostics for ThinkPads on Linux — a native GTK4/libadwaita system companion."* | Descriptive use of "ThinkPads" only, per trademark guidance in the plan. |
| Topics | `linux` `ubuntu` `gnome` `gtk4` `libadwaita` `thinkpad` `fwupd` `battery-health` `hardware-monitoring` `system-utility` `python` `pygobject` | Discoverability across the audiences that will actually search for this. |
| License | GPL-3.0-or-later | Per ADR-0002. |
| Visibility | **Public from day one** | Open development; the hygiene files land in the first four commits anyway. "Public" ≠ "announced" — the announcement gate (alpha, end of M2) is unchanged. |
| Default branch | `main` | — |
| Merge policy | **Squash-merge only** (merge commits and rebase-merge disabled) | Per §16: one commit per PR, conventional-commit subject, greppable history. |
| Branch protection on `main` | Require PR + green **fast-lane CI**; linear history; no force-push | All work via PRs even solo — the PR is where the DoD checklist and agent review happen. |
| Features to enable | Issues, issue forms, **private vulnerability reporting**, Dependabot alerts | Private vuln reporting is what SECURITY.md will point at. Discussions deferred until there's a community. |
| Application ID (reverse-DNS) | **Decision needed at ADR-0001 time, before Commit 6** | The `.desktop`, metainfo, gschema, and polkit action names all embed it. Two options: register **`lapcare.dev`** → use `dev.lapcare.LapCare` / `dev.lapcare.*` actions (what plan v1.1 assumed), or use **`io.github.<gh-username>.lapcare`** (GNOME-sanctioned, zero cost, no domain to own). Recommendation: the `io.github.…` form unless you intend to buy the domain — polkit action names are annoying to migrate later, so decide once. |

---

# Part B — Phase 1: Where Every Existing Document Goes

Principle: the three standalone documents are **historical records** — they get archived
verbatim (frozen, never edited), and their *living* content is extracted into the repo's
canonical documents. One fact, one home; history stays honest.

## B.1 Existing documents

### `lapcare-engineering-plan.md` (v1.1)
- **Destination:** `docs/history/2026-07-engineering-plan-v1.1.md`
- **Renamed:** yes (dated, versioned).
- **Split:** yes — this is the master split. It stops being a living document the moment the
  repo exists; each section's content moves to its canonical home:

| Plan section | Canonical home in repo |
|---|---|
| §1 Product Vision, §2 Guiding Principles | `PROJECT_CONSTITUTION.md` (principles, invariants); one-paragraph pitch also into `README.md` |
| §3 Architecture Overview, §6 Backend, §7 UI, §8 Module Boundaries | `ARCHITECTURE.md` (diagram, layers, data-flow rule, import table, concurrency model) |
| §4 Technology Stack | `ARCHITECTURE.md` (summary table) + ADR-0003 (the decision + alternatives) |
| §5 Framework recommendation | **ADR-0003** (`docs/adr/0003-ui-stack-gtk4-python.md`) — justification and rejected alternatives belong in the ADR, not the architecture doc |
| §6 provider table (planned providers) | `ROADMAP.md` appendix for now; migrates to `docs/modules/providers.md` in M1 when providers actually exist |
| §9 Directory layout | `ARCHITECTURE.md` (as-built tree, updated as it grows) |
| §10 Coding standards | `STYLEGUIDE.md` |
| §11 Logging, §12 Error handling | `STYLEGUIDE.md` (rules) + `ARCHITECTURE.md` (exception hierarchy, journal decision) |
| §13 Security considerations | `docs/security-design.md` (threat model & rules; distinct from SECURITY.md which is *reporting policy*) |
| §14 Privilege strategy | **ADR-0004** (`0004-privilege-strategy-polkit-pkexec.md`) + summary in `ARCHITECTURE.md`; helper spec itself becomes ADR-0006 (written before M4, number reserved now) |
| §15 Testing strategy | `docs/testing.md` |
| §16 CI/CD | `CONTRIBUTING.md` (what contributors see) + workflow files themselves (M0 commits) |
| §17 Release strategy | `docs/release.md` (cadence, channels, staged labels); Flatpak deferral → **ADR-0005** |
| §18 Documentation strategy + Agent-First section | Consumed by the authored files themselves (`AGENTS.md`, `CONTRIBUTING.md`, `docs/` layout); the contracts-vs-recipes rule goes into `CONTRIBUTING.md` |
| §19–21 Milestones, MVP, future roadmap | `ROADMAP.md` |
| §22 Risks | `docs/risks.md` (living register, reviewed at each milestone close) |

### `lapcare-review-reconciliation.md`
- **Destination:** `docs/history/2026-07-architecture-review-reconciliation.md`
- **Renamed:** yes (dated). **Split:** no — archived verbatim.
- **Content that moves elsewhere:** the *decisions* it records become ADRs so agents find them
  in the normal place: capability-model deferral → **ADR-0008**; the D-Bus-service deferral and
  enumerate-and-match rule fold into **ADR-0004**; ADR-0006/0007 numbers reserved. Each derived
  ADR cites the reconciliation doc as context.

### `lapcare-architcture-review.md` (Principal Engineer review)
- **Destination:** `docs/history/2026-07-architecture-review.md` (typo in filename fixed).
- **Renamed:** yes. **Split:** no — archived verbatim as review-of-record.

### `lapcare-m0-bootstrap-plan.md` (this document)
- **Destination:** `docs/history/2026-07-m0-bootstrap-plan.md` once M0 completes; while M0 is
  executing, its commit checklist is mirrored into `docs/status/m0-skeleton-and-rails.md`
  (the living tracker).

## B.2 Documents to create before coding begins (M0 Commits 1–5)

| Document | Path | Contents |
|---|---|---|
| `PROJECT_CONSTITUTION.md` | root | Vision (from §1), the 9 guiding principles (§2), and the **non-negotiable invariants**: wrap-don't-reimplement; ports-and-adapters dependency rule; least privilege / read-only-by-default; graceful degradation as a feature contract; agent-legibility. Changes to this file require an ADR. `AGENTS.md` links here instead of restating principles. |
| `AGENTS.md` | root | ≤150 lines: project summary, layer diagram, import table, task-type routing table, run/check commands, hard prohibitions. Written per the Agent-First spec in plan §Agent-First. |
| `CONTRIBUTING.md` | root | Workflow, commit conventions, **Definition of Done** (a named section — not a separate file, so it lives where PRs link to it), contracts-vs-recipes doc rule, fixture-capture policy pointer. DoD: code + tests + docs updated + status-file tick + `./check` green + strings translatable + no new deps without ADR. |
| `README.md` | root | User-facing: pitch, status banner ("pre-alpha — nothing to install yet"), planned features, build-from-source, links to constitution/architecture. |
| `CHANGELOG.md` | root | Keep-a-Changelog format, `[Unreleased]` section. |
| `SECURITY.md` | root | Supported versions (none yet), private-vulnerability-reporting instructions (GitHub PVR), response expectations, scope note re: privileged helper. Created in M0 even though the gate is M4 — it costs nothing now. |
| `CODE_OF_CONDUCT.md` | root | Contributor Covenant 2.1, maintainer contact. |
| `ARCHITECTURE.md` | root | As mapped above; ≤2 pages, links into `docs/`. |
| `STYLEGUIDE.md` | root | As mapped above; every rule with a right/wrong example pair. |
| `ROADMAP.md` | root | Milestones M0–M5 + future M6–M11, acceptance criteria, status markers, release-label mapping (M0→0.1.0 … M2→0.3.0 alpha, M3→0.4.0 beta, M5→1.0). |
| `DECISIONS.md` | root | ADR index incl. **reserved** rows for 0006 (helper threat model — gate for M4) and 0007 (async per LTS — written during M0 spike). |
| ADR template | `docs/adr/template.md` | Title / Status (Proposed·Accepted·Superseded-by) / Date / Context / Decision / Consequences / Alternatives considered. |
| ADRs 0001–0005, 0008 | `docs/adr/` | 0001 naming & app-id; 0002 license; 0003 UI stack; 0004 privilege strategy; 0005 Flatpak deferred; 0008 capability model deferred (availability() as seed, M6/M10 trigger). |
| PR template | `.github/PULL_REQUEST_TEMPLATE.md` | Embeds the DoD checklist + "which milestone/status file does this tick?" |
| Issue templates | `.github/ISSUE_TEMPLATE/` | `bug_report.yml` (model, kernel, tool versions, journal excerpt), `feature_request.yml`, `hardware_report.yml` (fixture-contribution intake — asks for *redacted* captures only), `config.yml` (blank-issues off, security → SECURITY.md). |
| Milestone status file | `docs/status/m0-skeleton-and-rails.md` | M0 acceptance criteria as a checkbox list; ticked commit-by-commit. |
| `docs/testing.md`, `docs/release.md`, `docs/risks.md`, `docs/security-design.md` | `docs/` | As mapped above. |
| `.gitignore`, `LICENSE` | root | Python/Meson/builddir ignores; GPL-3.0-or-later text. |

**Deliberately NOT created in M0** (per reconciliation, finding #14): `docs/guides/*` recipes
(extracted from real code at end of M1), `docs/modules/*` (need real modules), `docs/user/*`
(nothing to use yet).

## B.3 Target tree at end of M0

```
lapcare/
├── AGENTS.md  ARCHITECTURE.md  CHANGELOG.md  CODE_OF_CONDUCT.md  CONTRIBUTING.md
├── DECISIONS.md  LICENSE  PROJECT_CONSTITUTION.md  README.md  ROADMAP.md
├── SECURITY.md  STYLEGUIDE.md
├── run  check                      # dev wrappers
├── meson.build  meson.options  pyproject.toml
├── .gitignore
├── .github/
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── ISSUE_TEMPLATE/{bug_report,feature_request,hardware_report,config}.yml
│   ├── dependabot.yml
│   └── workflows/ci.yml            # fast + full lanes
├── data/                           # .desktop, metainfo.xml, gschema, icons
├── debian/                         # packaging skeleton (control, rules, …)
├── docs/
│   ├── adr/  (template + 0001–0005, 0007, 0008; 0006 reserved)
│   ├── history/  (the three archived documents + this plan, post-M0)
│   ├── status/m0-skeleton-and-rails.md
│   ├── testing.md  release.md  risks.md  security-design.md
├── src/lapcare/
│   ├── app.py  __init__.py
│   ├── core/{__init__.py, ports.py}          # stubs, real content M1+
│   ├── providers/__init__.py
│   ├── platform/{__init__.py, log.py, scheduler.py}
│   └── ui/{__init__.py, window.py, window.blp, pages/placeholder/…}
├── tests/{unit/, smoke/, conftest.py}
└── tools/stack_probe.py            # per-LTS environment probe (from the M0 spike)
```

---

# Part C — Phase 2: Milestone M0 Commit-by-Commit Plan

**M0 objective (from ROADMAP):** empty-but-running app plus all rails, contracts docs, and the
per-LTS stack validation. **Exit:** `./run` opens a window and `./check` passes on both
supported Ubuntu LTS releases (24.04, 26.04); async mechanism per LTS recorded in ADR-0007;
CI both lanes green; tag `v0.1.0`.

Conventions: every commit = one PR, squash-merged, fast-lane green. Effort scale:
**S** ≤ 1 h · **M** 1–3 h · **L** 3–6 h (focused implementation + self-review; agent-executed
commits still get human review at these sizes).

Sequencing logic: governance docs first (they're the contracts agents execute against), then
build/tooling rails, then the spike (riskiest unknown — front-loaded before any code depends
on its answer), then the app skeleton, then CI hardening and packaging, then milestone close.

---

**Commit 1 — `chore: initialize repository skeleton`**
- *Purpose:* a legally and structurally valid empty repo.
- *Files:* `LICENSE`, `.gitignore`, `README.md` (stub with status banner), `CHANGELOG.md`.
- *Acceptance:* GitHub detects GPL-3.0; README states pre-alpha status honestly.
- *Deps:* repo created with Part A settings. *Effort:* S.

**Commit 2 — `docs: project constitution and community policies`**
- *Purpose:* the non-negotiables and the safety/conduct surface, before anything references them.
- *Files:* `PROJECT_CONSTITUTION.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`.
- *Acceptance:* constitution contains vision + 9 principles + invariants and the "changes
  require an ADR" rule; SECURITY.md points at GitHub private vulnerability reporting (enabled);
  CoC has a real contact address.
- *Deps:* C1. *Effort:* M.

**Commit 3 — `docs: architecture document and decision records`**
- *Purpose:* canonical architecture + the ADR system, including archiving the source documents.
- *Files:* `ARCHITECTURE.md`, `DECISIONS.md`, `docs/adr/template.md`, ADRs 0001–0005 + 0008,
  `docs/history/` (three archived docs per Part B.1), `docs/security-design.md`, `docs/risks.md`.
- *Acceptance:* every ADR follows the template with Status: Accepted; DECISIONS.md indexes all
  ADRs including reserved 0006/0007 rows; ARCHITECTURE.md ≤ 2 pages containing the layer
  diagram, import table, and concurrency model; ADR-0001 records the final app-id decision
  (needed by C6). History files byte-identical to the approved originals.
- *Deps:* C1; **app-id decision from Part A approved**. *Effort:* M.

**Commit 4 — `docs: agent guide, contributor guide, roadmap, milestone tracker`**
- *Purpose:* everything an agent or contributor reads before writing code.
- *Files:* `AGENTS.md`, `CONTRIBUTING.md` (incl. Definition of Done section), `STYLEGUIDE.md`,
  `ROADMAP.md`, `docs/status/m0-skeleton-and-rails.md`, `docs/testing.md`, `docs/release.md`.
- *Acceptance:* AGENTS.md ≤ 150 lines with routing table and hard prohibitions; DoD is an
  enumerated checklist; ROADMAP matches plan v1.1 §19–21 including release-label mapping;
  status file lists every M0 acceptance criterion as a checkbox (C1–C4 ticked by this commit).
- *Deps:* C2, C3 (links into them). *Effort:* M.

**Commit 5 — `chore: GitHub templates and automation config`**
- *Purpose:* PR/issue intake matches the process the docs promise.
- *Files:* `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/{bug_report,feature_request,hardware_report,config}.yml`, `.github/dependabot.yml`.
- *Acceptance:* PR template embeds the DoD checklist; bug form requires model/kernel/versions;
  hardware form states redaction requirement; blank issues disabled; security contact routes to
  SECURITY.md; templates render correctly on GitHub.
- *Deps:* C4 (DoD exists). *Effort:* S.

**Commit 6 — `build: Meson skeleton and Python package layout`**
- *Purpose:* the build system and the package tree with correct boundaries, before any logic.
- *Files:* `meson.build`, `meson.options` (libexecdir/polkitdir/app-id options), `run`,
  `src/lapcare/__init__.py` (version), `core/__init__.py`, `core/ports.py` (docstring stub),
  `providers/__init__.py`, `platform/__init__.py`, `ui/__init__.py`,
  `data/` (`.desktop`, `metainfo.xml`, minimal gschema — all using the ADR-0001 app-id).
- *Acceptance:* `meson setup build && meson compile -C build` succeeds; `./run` executes an
  entry point that logs version and exits 0 (no GUI yet); `meson install` places files per
  options; metainfo passes `appstreamcli validate`.
- *Deps:* C3 (app-id). *Effort:* M.

**Commit 7 — `chore: lint, type, import-contract, and test tooling`**
- *Purpose:* the mechanical guardrails, live before the first real code.
- *Files:* `pyproject.toml` (ruff, mypy — strict for `core`/`providers`, lenient `ui`; pytest;
  import-linter contracts encoding the §8 table), `check`, `tests/conftest.py`,
  `tests/unit/test_sanity.py` (imports every package, asserts version).
- *Acceptance:* `./check` runs ruff → mypy → lint-imports → pytest, all green; a deliberate
  cross-layer import (added then reverted in the PR to prove it) fails `lint-imports`.
- *Deps:* C6. *Effort:* M.

**Commit 8 — `ci: fast-lane workflow`**
- *Purpose:* every subsequent PR is gated.
- *Files:* `.github/workflows/ci.yml` (fast lane: newest-LTS container, runs `./check`),
  README badge.
- *Acceptance:* lane green on this PR; wall time < 5 min; branch protection switched to
  require it.
- *Deps:* C7. *Effort:* S.

**Commit 9 — `spike: per-LTS stack validation; ADR-0007 (async integration)`**
- *Purpose:* retire M0's riskiest unknown before app code depends on the answer: does
  `gi.events` (PyGObject ≥ 3.50) exist per LTS, do Blueprint/libadwaita/dbusmock versions
  suffice, and what exactly is the fallback on 24.04.
- *Files:* `tools/stack_probe.py` (prints PyGObject/GTK/Adw/blueprint/dbusmock versions and
  gi.events availability; kept — CI reuses it as a diagnostic), `docs/adr/0007-async-integration-per-lts.md`, `DECISIONS.md` update.
- *Acceptance:* probe output captured from real 24.04 and 26.04 containers and quoted in the
  ADR; ADR-0007 Accepted, specifying the mechanism per LTS and the platform-executor fallback
  contract; any version pins land in `meson.build`/docs.
- *Deps:* C6–C8 (needs the build + CI containers). *Effort:* **M–L — highest uncertainty in M0;
  if 26.04 also needs the fallback, scope of C11 grows but nothing else changes.**

**Commit 10 — `feat: application shell with logging`**
- *Purpose:* first real code — `Adw.Application` and the logging spine.
- *Files:* `src/lapcare/app.py` (application class, `--verbose`, `LAPCARE_DEBUG`),
  `src/lapcare/platform/log.py` (stdlib logging → stderr/journal, level rules from §11),
  `src/lapcare/ui/window.py` (empty `Adw.ApplicationWindow`), `run` update.
- *Acceptance:* `./run` opens an empty window on both LTS releases; startup logs visible via
  `journalctl --user`; `--verbose` enables DEBUG; `./check` green.
- *Deps:* C6, C7, C9. *Effort:* M.

**Commit 11 — `feat: platform async scheduler per ADR-0007`**
- *Purpose:* the one sanctioned way provider I/O will run, proven before providers exist.
- *Files:* `src/lapcare/platform/scheduler.py` (gi.events wiring where available; shared
  thread-pool + `GLib.idle_add` fallback behind the same interface), `tests/unit/test_scheduler.py`.
- *Acceptance:* a demo async task (sleep + result) completes without blocking the UI on both
  LTS mechanisms; interface identical either way; no ad-hoc threads outside this module
  (import-linter/grep check); tests pass without a display.
- *Deps:* C9, C10. *Effort:* M.

**Commit 12 — `feat: navigation shell and reference page with four-state pattern`**
- *Purpose:* the UI skeleton every future page copies — this commit *is* the future
  `adding-a-page.md` guide's source material.
- *Files:* `src/lapcare/ui/window.py` + `window.blp` (`Adw.NavigationSplitView`, sidebar),
  `ui/pages/placeholder/{page.blp, view.py, view_model.py}` (demonstrates loading / ready /
  unavailable / error via a debug state-switcher), blueprint compilation wired into Meson,
  `tests/unit/test_placeholder_view_model.py`.
- *Acceptance:* sidebar navigates; all four states render with correct `Adw.StatusPage`
  patterns; view-model tested without a display; all strings `_()`-wrapped; `./check` green.
- *Deps:* C10, C11. *Effort:* L.

**Commit 13 — `test: xvfb smoke test in CI`**
- *Purpose:* the "app launches and navigates without criticals" gate, forever.
- *Files:* `tests/smoke/test_launch.py`, `ci.yml` update (xvfb + `dbus-run-session`,
  GTK criticals fail the test).
- *Acceptance:* smoke test passes in CI; fast lane still < 5 min; a deliberately introduced
  critical (proven then reverted in the PR) fails the run.
- *Deps:* C8, C12. *Effort:* M.

**Commit 14 — `build: Debian packaging skeleton and full CI lane`**
- *Purpose:* prove installability on both LTS releases from day one (reconciliation #9/#15).
- *Files:* `debian/{control,rules,changelog,copyright,install}`, `ci.yml` full lane
  (main/nightly/tags: both-LTS matrix × `./check` + meson build + `dpkg-buildpackage`,
  artifact retained, install-and-launch check in container).
- *Acceptance:* `.deb` builds on 24.04 and 26.04 in CI; installing it places the desktop file,
  icons, and app correctly; `lapcare` launches from the installed package under xvfb.
- *Deps:* C6–C13. *Effort:* L — Debian packaging always eats a surprise; budget accordingly.

**Commit 15 — `docs: close milestone M0; release v0.1.0`**
- *Purpose:* honest milestone close per the workflow contract.
- *Files:* `docs/status/m0-skeleton-and-rails.md` (all criteria ticked or explicitly deferred
  with reasons), `CHANGELOG.md` (0.1.0), `ROADMAP.md` status flip, `README.md` (badge, build
  instructions), archive this plan to `docs/history/2026-07-m0-bootstrap-plan.md`.
- *Acceptance:* every M0 criterion resolved; tag `v0.1.0` pushed; full lane green on the tag;
  retrospective notes (tooling friction, spike findings) appended to the status file — they
  feed M1's guide-writing.
- *Deps:* all. *Effort:* S.

---

## Dependency graph (summary)

```
C1 → C2 → C3 → C4 → C5
      C1 → C3(app-id) → C6 → C7 → C8 → C9 → C10 → C11 → C12 → C13 → C14 → C15
                                   (C9 gates all app code)
```

Docs commits (C2–C5) and build commits (C6–C8) can proceed in parallel once C3's app-id
decision lands. Total estimate: **~15 commits, roughly 25–35 focused hours**, dominated by
C9 (spike), C12 (reference UI), and C14 (packaging).

## Out of scope for M0 (explicit)

No providers, no real pages, no polkit policy/helper (M4, gated on ADR-0006), no
`docs/guides/` or `docs/modules/` (end of M1), no gettext build wiring (strings are wrapped
from C12 onward; the build machinery lands by M5), no PPA upload (pipeline target is M5;
CI-built .deb suffices until then), no Flatpak (ADR-0005).

## Approval checklist (decisions needed before Commit 1)

1. Repository name **`lapcare`** and Part A metadata.
2. **App-id / reverse-DNS choice** (buy `lapcare.dev` → `dev.lapcare.*`, or use
   `io.github.<username>.lapcare`) — blocks C3/C6.
3. GitHub owner/org for the repo, and public-from-day-one visibility.
4. This commit plan as the M0 execution contract.
