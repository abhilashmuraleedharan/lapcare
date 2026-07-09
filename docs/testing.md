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

**Fixture schema (in force since M1):**

- Layout: `tests/fixtures/<source>/<machine-slug>/…` where `<source>` is the provider module
  name (`dmi`, `os_info`, `thinkpad_acpi`, `pci_usb`, …). Filesystem sources mirror paths
  from `/` (e.g. `dmi/thinkpad-e16-gen2/sys/class/dmi/id/sys_vendor`); command sources store
  one `<tool>.txt` per invocation.
- Machine slugs are kebab-case marketing names (`thinkpad-e16-gen2`) or `synthetic-*` for
  handcrafted pathological cases.
- Every community capture ships with the tool-generated `README.md` (machine, capture date,
  kernel, redaction status).
- `lapcare --capture-fixtures [DIR]` produces this layout; redaction is on by default.

**Review checklist for accepting a capture (maintainer, before merge):**

1. No identifiers anywhere: no serials, UUIDs, asset tags, MAC addresses, or real hostnames
   (grep the capture; the tool's README must NOT say "IDENTIFIERS INCLUDED").
2. Capture README present with machine + kernel recorded.
3. New quirks observed in the data are documented in the affected provider's module doc
   (`docs/modules/providers.md`) in the same PR.
4. At least one provider test asserts against the new fixture (a fixture no test reads is
   corpus rot).

## Manual hardware matrix

A per-release checklist executed on real hardware (maintainer machines + community testers
recruited via the hardware-report issue template). Grows from M1; lives in this file as the
matrix takes shape.

**Primary reference machine: ThinkPad E16 Gen 2 (maintainer's laptop).** Every feature must
work on this model before a milestone closes — it is the first fixture source and the first
manual-matrix entry. Note for providers: the E-series can differ from T/X-series in
thinkpad_acpi surface (fan reporting, LED set) — never assume T-series behavior is universal;
that's what the fixture corpus is for.

## Accessibility checklist (ROADMAP M5 criteria; re-check each release)

Audited at M5 across all six pages; the criteria and how each is met:

- **Full keyboard navigation** — stock GTK4/Adwaita widgets throughout (ListBox sidebar,
  ActionRow/ExpanderRow content, focusable buttons); app shortcuts `Ctrl+Q` (quit) and
  `Ctrl+W` (close window) registered in app.py. No custom widget captures focus.
- **Screen-reader labels on all rows** — every row is an Adw.ActionRow/ExpanderRow with a
  real title (accessible label for free); every button uses Adw.ButtonContent with a text
  label, never icon-only. The one drawing widget (WearChart) reports role IMG with a label
  that summarizes the series data (count, first/last day + wear).
- **No information by color alone** — every colored status (diagnostics verdicts, storage
  health summary, battery health class) pairs the CSS color with words carrying the same
  meaning ("Critical", "FAILING — back up your data now", "Good · 5% wear").
- **Respects font scaling** — no fixed-pixel text anywhere: WearChart's day labels are laid
  out with Pango from the widget's own font context (scaled, not cairo toy text), and the
  chart reserves label space from the actual font metrics at draw time.
