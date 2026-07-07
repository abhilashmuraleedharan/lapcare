# Lapcare Project Constitution

This document is the project's highest authority on *why Lapcare exists* and *what it will
never do*. Everything else — architecture, style, roadmap — is subordinate to it.
**Changes to this document require an accepted ADR** (see `DECISIONS.md`).

## Vision

Lapcare is a polished, modern desktop application for Ubuntu (and other Linux distributions)
that gives ThinkPad owners the system insight and hardware management they lost when they left
Windows and Lenovo Vantage behind: hardware information, battery health and wear analysis,
firmware updates, storage health, diagnostics, and exportable reports — in one native window.

It is explicitly **an integration layer, not a reimplementation layer**. Linux already has
excellent hardware tooling — `fwupd`, `upower`, `smartctl`, `lm-sensors`, `thinkpad_acpi`,
`dmidecode` — scattered across CLIs, D-Bus services, and sysfs files that ordinary users never
discover. Lapcare's job is to orchestrate those tools behind one coherent UI.

*One-sentence pitch: "Everything your ThinkPad can tell you, in one window."*

Success looks like:

- A ThinkPad user installs one package and immediately sees hardware info, battery health,
  firmware status, and a health overview — with zero terminal usage.
- A support-forum answer changes from "run these 6 commands and paste the output" to
  "export a diagnostic report from Lapcare and attach it."
- Contributors and AI agents can add a new hardware provider in an afternoon because the
  module boundaries and documentation make the extension point obvious.

## Guiding Principles

1. **Wrap, don't reimplement.** If a maintained Linux tool or kernel interface exposes the
   data, consume it. We write UI, orchestration, and interpretation — never device drivers or
   parsers for things that have a stable structured interface.
2. **Prefer structured interfaces over scraping.** D-Bus > sysfs > CLI with `--json` > CLI
   text parsing. Text parsing is a last resort, isolated behind a provider so it can be
   replaced.
3. **Degrade gracefully.** Every feature must handle "this tool isn't installed", "this isn't
   a ThinkPad", and "permission denied" as first-class states with helpful UI, not crashes.
4. **Least privilege, always.** The app runs as the user. Privileged operations go through
   narrowly-scoped polkit actions. No `sudo`, no setuid, no long-running root daemon in the
   MVP.
5. **Read-only by default.** The MVP observes; it does not mutate hardware state. Writes come
   later, individually, behind explicit polkit actions.
6. **Boring technology.** Choose tools that will still be maintained in 2036. Every
   dependency is a liability we adopt.
7. **Modular, not micro.** Clear module boundaries with plain interfaces — but one process,
   one repo, one language until proven insufficient.
8. **Agent-legible.** The repository is structured so an AI coding agent (or a new human
   contributor) can locate the architecture, conventions, current status, and past decisions
   in under five minutes of reading.
9. **Simplicity beats cleverness.** A 30-line explicit function beats a 5-line metaprogrammed
   one.

## Non-Negotiable Invariants

These are enforced mechanically where possible (CI) and by review everywhere else. Loosening
any of them requires an ADR — never a silent divergence.

1. **The dependency rule** (ports-and-adapters): `core` imports stdlib only and performs no
   I/O; providers and platform implement `core/ports.py` interfaces; the UI depends on core
   only (plus GTK); only the composition root sees concrete implementations. Enforced by
   import-linter in CI. See `ARCHITECTURE.md`.
2. **Provider isolation:** all knowledge of an external data source's quirks (paths, schemas,
   formats) lives inside exactly one provider module. Nothing else may parse that source.
3. **Graceful degradation is a feature contract:** every provider reports availability; every
   page renders `loading / ready / unavailable / error`. A missing tool is a guided
   empty-state, never a crash.
4. **Least privilege:** no `sudo`, no setuid binaries, no root daemon without an accepted ADR.
   Privileged surface grows only one narrowly-scoped polkit action at a time.
5. **Privacy by default:** exports and fixture captures redact serial numbers, UUIDs, and MAC
   addresses unless the user explicitly opts in; identifiers never appear in logs above DEBUG.
6. **Honest documentation:** docs describe current truth and recorded decisions; aspirational
   content lives only in `ROADMAP.md`. Stale docs are bugs. Documentation updates ship in the
   same PR as the change they describe.
7. **No new runtime dependencies without an ADR.**

## Scope Boundaries

- Target platform: Ubuntu LTS first; GNOME-first UI; distro-portable where practical.
  We do not abstract the UI toolkit.
- Target hardware: Lenovo ThinkPads first. Other hardware degrades gracefully; broader vendor
  support is a roadmap item, not an MVP promise.
- Lapcare is an independent community project, not affiliated with Lenovo. Trademarks
  ("ThinkPad", "Lenovo", "Vantage") are used descriptively only and never in product naming.

## Provenance

Adopted from Engineering Plan v1.1 (see `docs/history/2026-07-engineering-plan-v1.1.md`),
approved 2026-07 after Principal Engineer review
(`docs/history/2026-07-architecture-review-reconciliation.md`).
