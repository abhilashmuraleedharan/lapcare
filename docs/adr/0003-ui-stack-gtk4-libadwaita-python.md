# ADR-0003: UI stack is GTK4 + libadwaita in Python (PyGObject), layouts in Blueprint

- **Status:** Accepted
- **Date:** 2026-07-06
- **Deciders:** Project owner, Lead Architect (confirmed by Principal Engineer review)

## Context

Lapcare targets Ubuntu Desktop (GNOME) first. Its integration surface is GLib-shaped: UPower,
fwupd, and logind are D-Bus services, and GDBus ships with GLib. The app is ~90% glue and
orchestration; performance is irrelevant (it reads sysfs files and makes D-Bus calls).
Primary contributors will include AI coding agents, so iteration speed and code legibility
weigh heavily. The app must look and feel native on the target platform to fulfill its
product promise.

## Decision

We will build the UI with **GTK4 + libadwaita ≥ 1.4 via PyGObject (Python 3.12+)**, define
all layouts declaratively in **Blueprint** (`.blp`, compiled to GTK Builder XML by
blueprint-compiler at build time), follow the GNOME HIG as the tiebreaker for UI arguments,
prefer stock Adwaita widgets, and position the product as **GNOME-first, distro-portable
where practical** — explicitly *without* a UI-toolkit abstraction layer.

## Consequences

- Native GNOME look, dark mode, adaptive layouts, and accessibility stack for free; reference
  implementations to imitate (GNOME Firmware, Mission Center).
- D-Bus access comes in-process with the toolkit (GDBus); no extra D-Bus dependency.
- KDE/other-DE users get a functional but GNOME-flavored app — accepted trade-off.
- Python's PyGObject asyncio integration varies by LTS; handled by ADR-0007.
- We accept mypy leniency in the UI layer (PyGObject stubs are imperfect); core/providers
  remain strict.

## Alternatives Considered

- **Qt6 (PySide):** technically excellent; rejected because Qt apps feel foreign on GNOME,
  packaging/licensing is heavier, and it would add its own D-Bus layer beside GDBus.
- **Rust + gtk4-rs:** best-in-class robustness; rejected for slower iteration on UI-heavy
  glue and a smaller contributor/agent success rate. Revisit only if a long-running system
  daemon is ever needed (that component could be Rust independently).
- **Tauri:** two languages plus an IPC boundary (Rust backend + JS frontend) for no benefit;
  webview sandbox friction against system access.
- **Electron:** footprint and non-native feel disqualifying for a system utility.
- **Imperative widget code instead of Blueprint:** rejected; declarative `.blp` files are
  diff-friendly and far more agent-editable.
