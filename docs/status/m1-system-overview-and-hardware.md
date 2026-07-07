# M1 — System Overview & Hardware Information: Status

**State:** COMPLETE (v0.2.0). **Branch:** `feature/m1` (single milestone PR, rebase-merged).
**Objective (ROADMAP):** Dashboard page (model, BIOS, kernel, uptime, quick stats) +
Hardware page (DMI identity, CPU/memory summary, PCI/USB inventory). Providers: `dmi`,
`os_info`, `pci_usb`, `thinkpad_acpi` (detection only). Graceful banner on non-ThinkPads.
Fixture governance before any community capture. Close = tag `v0.2.0`.

**Reference hardware:** ThinkPad E16 Gen 2 (maintainer's machine; containers see host
sysfs, so all validation runs against it). Probed 2026-07-07: LENOVO / 21MBCTO1WW /
family+version "ThinkPad E16 Gen 2" / BIOS R2JET48W(1.25) / `thinkpad_acpi` loaded.

## Commit plan

- [x] C1 `docs: open milestone M1`
- [x] C2 `feat(core): errors, models, and ports for M1 providers` — core/errors.py
      (plan §12 hierarchy), core/models.py (SystemIdentity, OsInfo, CpuMemSummary,
      PciDevice, UsbDevice, ThinkpadInfo), Availability + provider Protocols in
      core/ports.py; unit tests.
- [x] C3 `feat(platform): audited subprocess runner and sysfs read helpers` —
      platform/subprocess.py (argv whitelist, mandatory timeout, shell-free, async),
      platform/files.py (size-limited reads, None-on-missing); tests.
- [x] C4 `provider: os_info` — /etc/os-release + /proc (kernel, uptime, hostname,
      CPU model/counts, memory total); root-path injectable; fixture tests.
- [x] C5 `provider: dmi` — /sys/class/dmi/id identity fields (all Optional;
      product_serial expected PERMISSION_DENIED unprivileged); fixture tests.
- [x] C6 `provider: thinkpad_acpi (detection only)` — driver presence + DMI vendor
      cross-check → ThinkpadInfo; fixture tests incl. non-ThinkPad fixture.
- [x] C7 `provider: pci_usb` — inventory via `lspci -mm` / `lsusb` through the audited
      runner (runner-injectable); fixture tests; pciutils/usbutils added to deps.
- [x] C8 `feat: fixture capture tool + first real fixtures` — `lapcare --capture-fixtures`
      (headless; capture-time redaction of serials/UUIDs/MACs by default,
      --include-identifiers local-only); fixture schema + review checklist in
      docs/testing.md; first fixtures captured from the E16 Gen 2.
- [x] C9 `feat(ui): Dashboard page` — view-model consuming identity/os/thinkpad ports
      via the scheduler; four-state; non-ThinkPad Adw.Banner; wired in app.py.
- [x] C10 `feat(ui): Hardware page` — identity, CPU/memory, PCI/USB expander lists;
      smoke test navigates all pages.
- [x] C11 `docs: guides extracted from real code` — adding-a-provider, adding-a-page,
      capturing-fixtures; docs/modules/ for shipped modules.
- [x] C12 `docs: close milestone M1; release v0.2.0`.

## Acceptance criteria (from ROADMAP)

- [x] Dashboard shows model, BIOS version, kernel, uptime on the E16 Gen 2 — values
      verified against direct sysfs/proc reads (xvfb run: model=ThinkPad E16 Gen 2)
- [x] Hardware page shows DMI identity, CPU/memory summary, PCI/USB inventory
- [x] Non-ThinkPad shows the graceful banner (validated via QEMU fixture in VM tests)
- [x] Every panel handles `unavailable` (validated by fixture-driven tests)
- [x] Correct data verified on the E16 Gen 2 (fixtures + live xvfb runs against host sysfs). DEFERRED: second real ThinkPad — no second machine available; first community capture or maintainer access closes this (tracked for M2).
- [x] Fixture governance in place: schema documented, capture-time redaction default,
      review checklist — before any community capture is merged
- [x] `docs/guides/` recipes extracted from the real providers/pages built here
- [x] `docs/modules/` docs for shipped providers (exact paths/invocations + quirks)
- [x] ./check + smoke green on both LTS; fast lane green; full lane green at close (verified on tag)
- [x] Tag `v0.2.0`; CHANGELOG; ROADMAP flipped (tag pushed on merge)

## Known deferrals / notes

- Second real-ThinkPad validation deferred (single machine available); the corpus and
  hardware-report intake exist — close via first community capture (target: during M2).
- Uptime is a static snapshot (no live refresh yet); live updates arrive with M2's
  UPower work.
- Sidebar icons and USB root-hub filtering: M5 polish.

## Retrospective

- **Containers seeing host sysfs made real-hardware validation possible pre-upgrade** —
  the E16 Gen 2 was probed, captured, and rendered live entirely through the container
  harness. The fixture corpus started with REAL data on day one.
- **The rails caught the architect:** import-linter flagged the UI type-importing
  platform.scheduler; the fix (Scheduler Protocol into core/ports.py) made the
  architecture more honest. Exactly what the rails are for.
- **Two masked-failure lessons:** grep-gating swallowed a check failure twice; local
  gates now use exit codes. Also: verify with ./check, not just the targeted test.
- **Real data beats assumptions:** the E16's BIOS string has an internal space; new
  silicon shows 'Device XXXX' until pci.ids catches up — both now recorded in
  docs/modules/providers.md instead of being 'fixed' away.
- **For M2:** UPower dbusmock template + battery_sysfs provider follow the established
  recipe; HistoryStore port lands in core/ports.py alongside Scheduler.
