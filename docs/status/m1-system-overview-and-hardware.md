# M1 — System Overview & Hardware Information: Status

**State:** in progress. **Branch:** `feature/m1` (single milestone PR, rebase-merged).
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
- [ ] C9 `feat(ui): Dashboard page` — view-model consuming identity/os/thinkpad ports
      via the scheduler; four-state; non-ThinkPad Adw.Banner; wired in app.py.
- [ ] C10 `feat(ui): Hardware page` — identity, CPU/memory, PCI/USB expander lists;
      smoke test navigates all pages.
- [ ] C11 `docs: guides extracted from real code` — adding-a-provider, adding-a-page,
      capturing-fixtures; docs/modules/ for shipped modules.
- [ ] C12 `docs: close milestone M1; release v0.2.0`.

## Acceptance criteria (from ROADMAP)

- [ ] Dashboard shows model, BIOS version, kernel, uptime on the E16 Gen 2 — values
      verified against direct sysfs/proc reads
- [ ] Hardware page shows DMI identity, CPU/memory summary, PCI/USB inventory
- [ ] Non-ThinkPad shows the graceful banner (validated via non-ThinkPad fixture and a
      container without Lenovo DMI)
- [ ] Every panel handles `unavailable` (validated by fixture-driven tests)
- [ ] Correct data on 2+ real ThinkPads incl. E16 Gen 2 (second machine: community or
      deferred with note at close)
- [x] Fixture governance in place: schema documented, capture-time redaction default,
      review checklist — before any community capture is merged
- [ ] `docs/guides/` recipes extracted from the real providers/pages built here
- [ ] `docs/modules/` docs for shipped providers (exact paths/invocations + quirks)
- [ ] ./check + smoke green on both LTS; fast lane green; full lane green at close
- [ ] Tag `v0.2.0`; CHANGELOG; ROADMAP flipped

## Known deferrals / notes

_(filled as they arise)_

## Retrospective (filled at close)

_TBD._
