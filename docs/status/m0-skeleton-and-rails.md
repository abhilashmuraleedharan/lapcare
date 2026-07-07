# M0 — Skeleton & Rails: Status

**State:** in progress. **Branch:** `feature/m0` (single milestone PR, rebase-merged).
**Execution contract:** `docs/history/2026-07-m0-bootstrap-plan.md` (Part C).
**Exit:** all acceptance criteria below checked (or explicitly deferred with reason);
tag `v0.1.0`.

## Commit progress

- [x] C1 `chore: initialize repository skeleton` (on `main` as root commit)
- [x] C2 `docs: project constitution and community policies`
- [x] C3 `docs: architecture document and decision records`
- [x] C4 `docs: agent guide, contributor guide, roadmap, milestone tracker` (this commit)
- [x] C5 `chore: GitHub templates and automation config`
- [x] C6 `build: Meson skeleton and Python package layout`
- [x] C7 `chore: lint, type, import-contract, and test tooling`
- [x] C8 `ci: fast-lane workflow`
- [x] C9 `spike: per-LTS stack validation; ADR-0007`
- [x] C10 `feat: application shell with logging`
- [x] C11 `feat: platform async scheduler per ADR-0007`
- [x] C12 `feat: navigation shell and reference page (four-state pattern)`
- [x] C13 `test: xvfb smoke test in CI`
- [x] C14 `build: Debian packaging skeleton and full CI lane`
- [ ] C15 `docs: close milestone M0; release v0.1.0`

## Acceptance criteria

- [x] `./run` opens a window on Ubuntu 24.04 LTS and 26.04 LTS (validated via xvfb in containers)
- [x] `./check` (ruff + mypy + import-linter + pytest) passes on both LTS releases
- [x] Async mechanism per LTS validated and recorded in ADR-0007
- [x] Import-linter demonstrably fails on a deliberate layering violation
- [x] CI fast lane green and < 5 min; required on `main` via branch protection (51 s first run)
- [ ] CI full lane: both-LTS matrix, meson build, .deb build + install-launch check
- [x] xvfb smoke test: app launches, navigates, zero GTK criticals (fails on deliberate critical — proven)
- [x] Reference page demonstrates all four page states; view-model tested without display
- [x] Contracts docs exist: constitution, ARCHITECTURE, STYLEGUIDE, CONTRIBUTING, AGENTS,
      ROADMAP, DECISIONS + ADRs 0001–0005, 0008 (0006/0007 reserved)
- [x] SECURITY.md, CODE_OF_CONDUCT.md published
- [x] GitHub templates (PR, issues) live
- [ ] Tag `v0.1.0` created; CHANGELOG updated; ROADMAP status flipped

## Known deferrals / notes

- `docs/guides/` and `docs/modules/` intentionally absent until end of M1 (contracts vs.
  recipes rule).
- gettext build wiring deferred to M5; strings are `_()`-wrapped from C12 onward.
- PPA upload deferred to M5; CI-built .deb is the artifact until then.

## Retrospective (filled at close)

_TBD._
