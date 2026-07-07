# AGENTS.md — Entry Point for AI Coding Agents

Read this first, every session. It routes to everything else; don't guess where truth lives.

## What this project is

Lapcare: a GTK4/libadwaita desktop app (Python 3.12+) giving ThinkPad users battery health,
hardware info, firmware updates (fwupd), storage health, and diagnostics on Linux. It **wraps
existing Linux tools** (D-Bus services, sysfs, CLIs) — it never reimplements them. Vision and
non-negotiable invariants: `PROJECT_CONSTITUTION.md`.

## Architecture in one diagram

```
UI (GTK4/libadwaita, Blueprint)  →  depends on core only
Core (pure Python, no I/O)       →  models + ports.py (all Protocol interfaces)
Providers (adapters)             →  implement core ports; one module per data source
Platform (D-Bus, subprocess,     →  implements core ports (HistoryStore, ReportWriter);
  scheduler, settings, logging)     owns all OS plumbing
app.py                           →  composition root; the ONLY place wiring concretes
```

Import rules (enforced by import-linter; violations fail CI):

| Module | May import | Must NOT import |
|---|---|---|
| `core/` | stdlib only | GTK/GLib, providers, platform, ui |
| `providers/` | core, platform | ui |
| `platform/` | stdlib, GLib, core ports | providers, ui |
| `ui/` | core only, GTK/Adw | providers, platform |
| `app.py` | everything | — |

## Before you write code

1. Check `ROADMAP.md` for what's in scope *now*, and `docs/status/<milestone>.md` for what
   actually exists vs. what's aspirational. Never implement future-milestone features.
2. Check `DECISIONS.md` — if your idea contradicts an accepted ADR, you need a superseding
   ADR, not a silent divergence.
3. Read `STYLEGUIDE.md` alongside any code-writing task.
4. Find the recipe for your task type (table below).

## Task-type routing

| Task | Read |
|---|---|
| Adding a provider | `docs/guides/adding-a-provider.md` (exists from M1) |
| Adding a UI page | `docs/guides/adding-a-page.md` (exists from M1) |
| Adding a diagnostic check | `docs/guides/adding-a-diagnostic.md` (exists from M4) |
| Capturing hardware fixtures | `docs/guides/capturing-fixtures.md` (exists from M1) |
| Anything architectural | `ARCHITECTURE.md`, then the relevant ADR |
| Security-relevant change | `docs/security-design.md` + ADR-0004 |
| Testing approach | `docs/testing.md` |
| Release/packaging | `docs/release.md`, ADR-0005 |

## Commands

```
./run      # build + launch the app
./check    # lint + format check + mypy + import-linter + tests (mirrors CI fast lane)
```

Both must pass before any commit. CI fast lane runs `./check`; the full lane adds the
both-LTS matrix and .deb build on main/tags.

## Definition of done (full version in CONTRIBUTING.md)

Code + tests + docs updated in the same PR + milestone status file ticked + `./check` green +
user-visible strings `_()`-wrapped + commit message follows conventional commits with DCO
sign-off.

## Hard prohibitions

- **Never** violate the import table above.
- **No new runtime dependencies** without an accepted ADR.
- **No `shell=True`**, no subprocess outside `platform/subprocess.py`, no ad-hoc threads
  (async goes through `platform/scheduler.py` per ADR-0007).
- **No `sudo`/setuid/root daemons**; privileged work only via the ADR-0004 polkit model.
- **No GTK imports in `core/`**; no business logic in views; no widget construction in
  view-models.
- **Never log or export serials/UUIDs/MACs** above DEBUG or without explicit user opt-in.
- **Don't edit generated files** (compiled Blueprint output, build artifacts).
- **Don't edit `docs/history/`** — those files are frozen records.
- **Don't parse a tool's output outside its one provider module.**
- Every model field is `Optional` unless the fixture corpus proves it universal; absence of
  hardware is data (empty list), inability to ask is `ProviderUnavailable`.

## UI conventions (the two you'll forget)

Every page renders exactly one of `loading / ready / unavailable(reason, remedy) /
error(detail)` via `Gtk.Stack`. Layouts are Blueprint (`.blp`) only — no imperative widget
trees. Prefer stock Adwaita widgets; custom widgets need justification in the PR.
