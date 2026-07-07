# Lapcare Architecture

One-page summary of how Lapcare is built. Decisions and their rationale live in ADRs
(`DECISIONS.md`); rules with examples live in `STYLEGUIDE.md`; the full planning history is
in `docs/history/`.

## Overview

Single desktop process (Python 3.12+, GTK4 + libadwaita via PyGObject) with strictly layered
internals, plus a short-lived privileged helper invoked through polkit (ships in M4,
gated on ADR-0006).

```
┌───────────────────────────────────────────────────────────┐
│  UI Layer (GTK4 + libadwaita, Blueprint)                  │
│  Pages, widgets, view-models. No system access.           │
├───────────────────────────────────────────────────────────┤
│  Core / Domain Layer (pure Python, no I/O)                │
│  Models, wear analysis, health scoring, diagnostics,      │
│  report rendering — and core/ports.py: the Protocol       │
│  interfaces that providers and platform implement.        │
├───────────────────────────────────────────────────────────┤
│  Provider Layer (integration adapters)                    │
│  upower · fwupd · battery_sysfs · thinkpad_acpi · hwmon · │
│  dmi · storage_smart · pci_usb · os_info                  │
│  One provider per data source; each fakeable in tests.    │
├───────────────────────────────────────────────────────────┤
│  Platform Layer                                           │
│  D-Bus connections, audited subprocess runner, privileged │
│  helper client, async scheduler, HistoryStore (SQLite),   │
│  ReportWriter, GSettings, logging, XDG paths.             │
└───────────────────────────────────────────────────────────┘
        │ pkexec (polkit, M4+)               │ D-Bus (system bus)
        ▼                                    ▼
  lapcare-helper                    UPower, fwupd, logind …
  (fixed-verb, short-lived)         (enforce their own polkit)
```

## The Dependency Rule (Invariant #1 — enforced by import-linter in CI)

Ports-and-adapters around a pure core. All dependency arrows point inward to `core`.

| Module | May import | Must not import |
|---|---|---|
| `lapcare/core/` (incl. `ports.py`) | stdlib only | GTK/GLib, providers, platform, ui |
| `lapcare/providers/` | core (models + ports), platform | ui |
| `lapcare/platform/` | stdlib, GLib, core ports (to implement them) | providers, ui |
| `lapcare/ui/` | **core only** (models + ports), GTK/Adw | providers, platform |
| `lapcare/app.py` | everything (composition root) | — |
| `helper/` (separate top-level) | stdlib only | anything in `lapcare` |

The UI never names a concrete provider: it receives port implementations from the composition
root (`app.py`), the only module that wires concrete objects together. Dependency injection by
hand — no framework.

**Layering controls blast radius** (a hardware quirk stays inside one provider); it does not
control hardware *variance*. Variance is controlled by the fixture corpus, nullable-by-default
model fields, and the availability contract (below).

## Key Contracts

- **Transport preference:** D-Bus > sysfs > CLI with `--json` > CLI text parsing (isolated,
  last resort).
- **Availability:** every provider implements `availability()` → `OK / TOOL_MISSING /
  UNSUPPORTED_HARDWARE / PERMISSION_DENIED`; the UI renders these as guided empty-states.
  This is deliberately the seed of a future capability model (ADR-0008).
- **Model fields are `Optional` unless the fixture corpus proves them universal.** Absence is
  data ("no discrete GPU" = empty list); *inability to ask* is `ProviderUnavailable`.
- **Exceptions:** providers translate every underlying failure into the small core hierarchy —
  `ProviderUnavailable(reason)`, `ProviderTimeout`, `ProviderParseError`,
  `PrivilegedActionDenied`. Nothing above a provider sees a `CalledProcessError`. Unexpected
  exceptions are caught at the main-loop boundary and become a copyable error banner; the app
  never dies because one panel failed.
- **Page states:** every page renders exactly one of `loading / ready / unavailable(reason,
  remedy) / error(detail)` via `Gtk.Stack`. Hard convention.
- **Persistence boundary:** core computes; `HistoryStore` and `ReportWriter` are core ports
  implemented in `platform/` (SQLite under `~/.local/share/lapcare/`, filesystem writes).
  Report *rendering* to a string is pure core.

## UI Architecture

`Adw.ApplicationWindow` + `Adw.NavigationSplitView`: sidebar of pages (Dashboard, Hardware,
Battery, Firmware, Storage, Diagnostics). Lightweight MVVM: Blueprint views + thin widget
subclasses that only bind/forward; plain-GObject view-models that call core/port APIs
asynchronously and are testable without a display. No business logic in views. Live updates
via D-Bus signals where they exist; polling only where they don't (hwmon, 2 s, paused when
page not visible). Progressive startup: providers lazy-init per page; the Dashboard renders
cheap/cached signals first and enriches asynchronously.

## Concurrency

GTK main loop on the main thread; provider I/O is `async def`, core is synchronous and pure.
Async integration per LTS is recorded in **ADR-0007** (PyGObject ≥ 3.50 `gi.events` where
available; otherwise the platform-owned shared thread-pool scheduler marshaling via
`GLib.idle_add`). No ad-hoc threads anywhere else. Every external command runs through the
single audited subprocess runner (argv lists, no shell, mandatory timeouts).

## Privilege Model (ADR-0004)

Three tiers: (0) most of the app needs no privileges — sysfs/UPower/DMI reads are
unprivileged; (1) firmware operations delegate to fwupd's D-Bus API, inheriting fwupd's own
polkit policy and LVFS signature verification; (2) SMART/NVMe/full-DMI reads go through the
fixed-verb pkexec helper, one polkit action per verb, device targeting by
**enumerate-and-match** (the helper resolves bare device names against its own `/sys/block`
enumeration; it never accepts paths). No root daemon; that decision is revisited by ADR when
the first *write* feature arrives (M6). Full threat model: ADR-0006 (gates M4).

## Logging

Stdlib `logging`, logger per module, stderr → systemd user journal (no custom files or
rotation). `--verbose` / `LAPCARE_DEBUG=1` for DEBUG. Identifiers (serials, UUIDs, MACs)
never above DEBUG. Details in `STYLEGUIDE.md`.

## Directory Layout (as built — grows with milestones)

```
src/lapcare/
├── app.py               # Adw.Application, composition root
├── core/                # models.py, ports.py, analysis, diagnostics/, report.py
├── providers/           # one module per data source
├── platform/            # dbus, subprocess, scheduler, history, settings, log, paths
└── ui/                  # window, pages/<name>/{page.blp,view.py,view_model.py}, widgets/
helper/                  # lapcare-helper + polkit policy (M4)
data/                    # .desktop, metainfo, gschema, icons (app id: io.github.abhilashmuraleedharan.lapcare)
tests/                   # unit/, providers/ (fixtures), smoke/
docs/                    # adr/, history/, status/, guides/ (M1+), modules/ (M1+)
```
