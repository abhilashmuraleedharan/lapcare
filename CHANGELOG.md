# Changelog

All notable changes to Lapcare are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] — 2026-07-07 (Milestone M2: Battery Health & Wear — PUBLIC ALPHA)

**The first announced release.** Pre-1.0 alpha: read-only, zero privileged
operations. Supported targets: Ubuntu 24.04 LTS and 26.04 LTS. Reference
hardware: ThinkPad E16 Gen 2.

### Added

- **Battery page**: live charge status (state, percentage, time estimates)
  via UPower with change-signal updates; health classification (transparent
  thresholds: Good < 15% wear, Fair < 30%, Poor beyond) with wear percentage;
  cycle count; full-vs-design capacity; daily wear history with a
  wear-over-time chart; dual-battery support. Live status degrades to a note
  where UPower is unavailable — wear data still shows.
- Providers: `battery_sysfs` (both energy_*/charge_* unit families,
  ThinkPad quirks normalized) and `upower` (D-Bus, dbusmock-tested end to
  end including signals).
- Wear history persistence: SQLite under the XDG data dir; one idempotent
  snapshot per battery per day; survives restarts.
- `lapcare --capture-fixtures` now captures battery data (serial numbers
  excluded, as always).

## [0.2.0] — 2026-07-07 (Milestone M1: System Overview & Hardware Information)

Pre-alpha. Supported targets: Ubuntu 24.04 LTS and 26.04 LTS. Reference
hardware: ThinkPad E16 Gen 2.

### Added

- **Dashboard page**: model, machine type, vendor, BIOS version/date, OS,
  kernel, uptime — with a banner on non-ThinkPad machines.
- **Hardware page**: DMI identity, processor and memory summary, PCI and USB
  device inventory (expandable lists).
- Providers: `dmi` (sysfs identity), `os_info` (os-release + /proc),
  `thinkpad_acpi` (ThinkPad detection), `pci_usb` (lspci/lsusb through the
  audited runner). All fixture-tested, including real ThinkPad E16 Gen 2
  captures; every panel degrades gracefully (four-state pattern).
- `lapcare --capture-fixtures`: headless hardware capture with identifiers
  redacted at capture time (`--include-identifiers` is local-only); fixture
  schema + maintainer review checklist in docs/testing.md.
- Core domain layer: models, error hierarchy, ports (incl. the Scheduler
  port); platform: audited subprocess runner (whitelisted argv, timeouts,
  bounded output) and bounded sysfs readers.
- Guides extracted from the real code: adding-a-provider, adding-a-page,
  capturing-fixtures; provider quirk registry in docs/modules/providers.md.

## [0.1.0] — 2026-07-07 (Milestone M0: Skeleton & Rails)

Not a usable release: development skeleton and rails. Supported targets:
Ubuntu 24.04 LTS and 26.04 LTS.

### Added

- Application shell: GTK4/libadwaita window with NavigationSplitView, sidebar
  navigation, and a reference page demonstrating the four-state pattern
  (loading / ready / unavailable / error) with a debug state switcher.
- Async scheduler (ADR-0007): native `gi.events` integration on PyGObject
  ≥ 3.50; dedicated background loop thread + `GLib.idle_add` fallback on 24.04.
- Logging spine (stderr → systemd user journal; `--verbose` / `LAPCARE_DEBUG=1`).
- Build: Meson + Blueprint pipeline, gresource bundling, generated launcher,
  desktop/metainfo/gschema files validated as meson tests.
- Dev rails: `./run` and `./check` (with `--lts` container modes for any
  docker host), ruff + strict mypy + import-linter dependency contracts +
  pytest, `tools/stack_probe.py` environment diagnostic.
- CI: PR fast lane (< 5 min) and full lane (both-LTS matrix, xvfb smoke test,
  .deb build + install-launch verification, artifacts).
- Debian packaging skeleton (native format, dh + meson).
- Governance & docs corpus: PROJECT_CONSTITUTION, ARCHITECTURE, STYLEGUIDE,
  CONTRIBUTING (with Definition of Done), AGENTS, ROADMAP, DECISIONS +
  ADRs 0001–0005, 0007, 0008, SECURITY, CODE_OF_CONDUCT, GitHub templates.
- Repository skeleton: license (GPL-3.0-or-later), README, changelog.
