# Testing Strategy

Test what we own — orchestration, parsing, interpretation, state machines. Don't test the
kernel, GTK, or the wrapped tools. Gate: `./check` green = ruff + mypy + import-linter +
pytest; CI adds the xvfb smoke test and (full lane) packaging.

## Taxonomy

| Layer | Where | Approach |
|---|---|---|
| Core (pure logic) | `tests/unit/` | Pure functions, no mocks, milliseconds. Target ~100% branch coverage of `core/` — it is small and pure, so this is cheap. Wear math, health scoring, every diagnostic check, report rendering, redaction. |
| Providers | `tests/providers/` | Fixture-driven: providers take a root-path/runner parameter so captured data injects cleanly. D-Bus providers run against **python-dbusmock** (ships UPower and fwupd templates). |
| View-models | `tests/unit/` | Driven with fake ports; assert state transitions (loading → ready/unavailable/error). No display needed. |
| App smoke | `tests/smoke/` | One CI job under xvfb + `dbus-run-session`: launch with fake ports, navigate every page, fail on GTK criticals. Not screenshot testing. |
| Privileged helper (M4+) | `tests/helper/` | The security-critical surface: argument validation, enumerate-and-match, injection attempts. Runs unprivileged with the tool runner faked. Suite required by ADR-0006. |

## The fixture corpus (`tests/fixtures/`)

The crown jewels: captured real data — sysfs trees as directory snapshots, `smartctl --json`
outputs, fwupd device lists, `/proc/acpi/ibm` files — organized as
`tests/fixtures/<source>/<machine>/`, from real ThinkPads **and** pathological cases (missing
`cycle_count`, `charge_full > design`, dual batteries, non-ThinkPad machines). Every hardware
bug report should become a regression fixture.

**Governance (in force before any community capture is accepted; established in M1):**

1. A documented fixture schema (layout, required metadata: model, kernel, tool versions).
2. Capture-time redaction by default (`--capture-fixtures`); `--include-identifiers` is
   local-only and unredacted captures are never merged.
3. Maintainer review checklist: identifiers scrubbed; machine/kernel recorded; any new quirk
   documented in the provider's module doc.

## Manual hardware matrix

A per-release checklist executed on real hardware (maintainer machines + community testers
recruited via the hardware-report issue template). Grows from M1; lives in this file as the
matrix takes shape.
