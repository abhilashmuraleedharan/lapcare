# Lapcare

[![CI](https://github.com/abhilashmuraleedharan/lapcare/actions/workflows/ci.yml/badge.svg)](https://github.com/abhilashmuraleedharan/lapcare/actions/workflows/ci.yml)

> **Status: pre-alpha.** Nothing to install yet — the project is under active initial
> development. The first announced release will be the public alpha (v0.3.0); see the
> roadmap below.

**Lapcare** is a native Linux desktop application that gives ThinkPad owners the system
insight and hardware management they lost when they left Lenovo Vantage behind: hardware
information, battery health and wear analysis, firmware updates (via [fwupd]/LVFS), storage
health, one-click diagnostics, and exportable diagnostic reports — in one modern
GTK4/libadwaita window.

Lapcare is deliberately **an integration layer, not a reimplementation layer**. Linux already
has excellent hardware tooling (`fwupd`, `upower`, `smartctl`, `lm-sensors`, sysfs,
`thinkpad_acpi`); Lapcare orchestrates those tools behind one coherent, native-feeling UI
rather than reinventing them.

*"Everything your ThinkPad can tell you, in one window."*

[fwupd]: https://fwupd.org

## Planned MVP features

- System overview and full hardware information
- Battery health, wear analysis, and wear history
- Firmware/BIOS update management (fwupd/LVFS)
- Storage SMART/NVMe health
- One-click diagnostics with an explainable health dashboard
- Diagnostic report export (redacted by default)

Every feature degrades gracefully on missing tools, unsupported hardware, or declined
authorization. The MVP is read-only: Lapcare observes your hardware, it does not mutate it.

## Project documents

| Document | Purpose |
|---|---|
| `PROJECT_CONSTITUTION.md` | Vision, guiding principles, non-negotiable invariants |
| `ARCHITECTURE.md` | System architecture and module boundaries |
| `ROADMAP.md` | Milestones and current status |
| `CONTRIBUTING.md` | How to contribute (humans and AI agents) |
| `AGENTS.md` | Entry point for AI coding agents |
| `DECISIONS.md` | Index of architecture decision records |

(Documents land during milestone M0 — links go live as they are committed.)

## License

GPL-3.0-or-later. See `LICENSE`.

Lapcare is an independent community project. It is not affiliated with, endorsed by, or
sponsored by Lenovo. "ThinkPad" and "Lenovo" are trademarks of Lenovo, used here only to
describe hardware compatibility.
