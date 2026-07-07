# M0 — Skeleton & Rails: Status

**State:** COMPLETE (v0.1.0). **Branch:** `feature/m0` (single milestone PR, rebase-merged).
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
- [x] C15 `docs: close milestone M0; release v0.1.0` (this commit; tag on merge)

## Acceptance criteria

- [x] `./run` opens a window on Ubuntu 24.04 LTS and 26.04 LTS (validated via xvfb in containers)
- [x] `./check` (ruff + mypy + import-linter + pytest) passes on both LTS releases
- [x] Async mechanism per LTS validated and recorded in ADR-0007
- [x] Import-linter demonstrably fails on a deliberate layering violation
- [x] CI fast lane green and < 5 min; required on `main` via branch protection (51 s first run)
- [x] CI full lane: both-LTS matrix, meson build, .deb build + install-launch check
      (run 28838716406: both legs green, .deb artifacts uploaded for 24.04 and 26.04)
- [x] xvfb smoke test: app launches, navigates, zero GTK criticals (fails on deliberate critical — proven)
- [x] Reference page demonstrates all four page states; view-model tested without display
- [x] Contracts docs exist: constitution, ARCHITECTURE, STYLEGUIDE, CONTRIBUTING, AGENTS,
      ROADMAP, DECISIONS + ADRs 0001–0005, 0008 (0006/0007 reserved)
- [x] SECURITY.md, CODE_OF_CONDUCT.md published
- [x] GitHub templates (PR, issues) live
- [x] Tag `v0.1.0` created; CHANGELOG updated; ROADMAP status flipped (tag pushed on merge)

## Known deferrals / notes

- `docs/guides/` and `docs/modules/` intentionally absent until end of M1 (contracts vs.
  recipes rule).
- gettext build wiring deferred to M5; strings are `_()`-wrapped from C12 onward.
- PPA upload deferred to M5; CI-built .deb is the artifact until then.
- App icon is a stock symbolic placeholder; real icon by M5.
- .deb ships meson-bytecompiled .pyc (fine for our PPA; revisit dh_python3/pycompile
  conventions before any Debian-archive ambitions).

## Retrospective

- **The host constraint shaped the milestone:** the maintainer's laptop runs Ubuntu 22.04
  (below both targets), so the container harness (`./run|./check --lts`, dev-container.sh)
  became load-bearing on day one. Worth it: every validation ran on exactly the target
  environments. Containers must run as the host user — root-owned build artifacts and tool
  caches in the workspace bit us twice before the `-u` fix.
- **Spike earned its keep:** ADR-0007's fork was real (24.04 lacks gi.events; the thread-loop
  fallback works and both paths are CI-tested). `tools/stack_probe.py` kept as diagnostic.
- **Build-system gotchas recorded:** `glib-compile-resources` lives in `libglib2.0-dev-bin`;
  Meson prints errors to *stdout* (never fully silence it); a generated launcher file named
  like the Python package collides with blueprint batch-compile's mirrored output tree —
  launcher now generated from the root meson.build.
- **Process lesson (the one CI failure):** C13 was validated with the targeted smoke test
  only, not `./check` — an unformatted file reached CI. Rule reinforced: `./check` before
  every push, no exceptions.
- **For M1 guide-writing:** window/pages structure, the four-state stack pattern, template
  callbacks, and the redundant-selection re-parent guard are the exact material for
  `docs/guides/adding-a-page.md`.
- **Hardware baseline:** ThinkPad E16 Gen 2 recorded as primary reference machine
  (docs/testing.md, ROADMAP M1); first fixtures come from it once the M1 capture tool exists.
