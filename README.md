# Lapcare

[![CI](https://github.com/abhilashmuraleedharan/lapcare/actions/workflows/ci.yml/badge.svg)](https://github.com/abhilashmuraleedharan/lapcare/actions/workflows/ci.yml)

> **Status: public alpha (v0.3.0).** Read-only, zero privileged operations. Dashboard,
> Battery, and Hardware pages are usable today; see [Planned features](#planned-features)
> and `ROADMAP.md` for what's next.

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

## Available now (v0.3.0)

- System overview: model, BIOS, OS, kernel, uptime, ThinkPad detection (Dashboard)
- Battery health: live charge status, wear analysis, health classification, cycle count,
  daily wear history with chart, dual-battery support (Battery)
- Full hardware information: DMI identity, CPU/memory, PCI/USB inventory (Hardware)

## Planned features

- Firmware/BIOS update management (fwupd/LVFS) — M3
- Storage SMART/NVMe health — M4
- One-click diagnostics with an explainable health dashboard — M4
- Diagnostic report export (redacted by default) — M4

Every feature degrades gracefully on missing tools, unsupported hardware, or declined
authorization. Through 1.0, Lapcare is read-only: it observes your hardware, it does not
mutate it.

## Project documents

| Document | Purpose |
|---|---|
| `PROJECT_CONSTITUTION.md` | Vision, guiding principles, non-negotiable invariants |
| `ARCHITECTURE.md` | System architecture and module boundaries |
| `ROADMAP.md` | Milestones and current status |
| `CONTRIBUTING.md` | How to contribute (humans and AI agents) |
| `AGENTS.md` | Entry point for AI coding agents |
| `DECISIONS.md` | Index of architecture decision records |

## Installing the alpha

Download the `.deb` for your Ubuntu release from the
[v0.3.0 release page](https://github.com/abhilashmuraleedharan/lapcare/releases/tag/v0.3.0)
and install it:

```sh
sudo apt install ./lapcare_0.3.0_all-ubuntu-24.04.deb   # or -ubuntu-26.04.deb
```

A PPA is planned for the 1.0 release (see `docs/release.md`); until then, GitHub Releases
is the distribution channel.

## Building from source (development)

Supported build/runtime targets are Ubuntu 24.04 and 26.04 (see `ARCHITECTURE.md`).

```sh
./run                # build + launch (needs the toolchain: see tools/install-deps.sh)
./check              # lint + types + import contracts + tests (mirrors CI fast lane)

# On any host with Docker (e.g. an older Ubuntu):
./run --lts 24.04
./check --lts 26.04
```

CI builds installable `.deb` packages for both LTS releases on every push to
`main` (Actions → artifacts). Contributor workflow: `CONTRIBUTING.md`; AI
agents start at `AGENTS.md`.

## License

GPL-3.0-or-later. See `LICENSE`.

Lapcare is an independent community project. It is not affiliated with, endorsed by, or
sponsored by Lenovo. "ThinkPad" and "Lenovo" are trademarks of Lenovo, used here only to
describe hardware compatibility.
