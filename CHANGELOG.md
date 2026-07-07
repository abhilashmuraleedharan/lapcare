# Changelog

All notable changes to Lapcare are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
