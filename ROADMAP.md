# Lapcare Roadmap

Intent lives here; implementation truth lives in `docs/status/<milestone>.md`. Nothing from
milestone N+1 starts before N's acceptance criteria are met or explicitly re-scoped here
(with an ADR if architectural). Source: Engineering Plan v1.1 §19–21 (frozen in
`docs/history/`).

**Release labels:** every milestone close tags `0.N.0`. Two are announced: **M2 close =
public alpha** (read-only, zero privileges), **M3 close = beta** (firmware updates get a full
cycle of field testing before 1.0). `1.0` = MVP definition met, stable on two LTS releases.

| Milestone | Tag | Status |
|---|---|---|
| M0 — Skeleton & Rails | v0.1.0 | **Done** (`docs/status/m0-skeleton-and-rails.md`) |
| M1 — System Overview & Hardware Info | v0.2.0 | **Done** (`docs/status/m1-system-overview-and-hardware.md`) |
| M2 — Battery Health & Wear | v0.3.0 (public alpha) | **Done** (`docs/status/m2-battery-health-and-wear.md`) |
| M3 — Firmware Updates | v0.4.0 (beta) | **Done** (`docs/status/m3-firmware-updates.md`) |
| M4 — Storage, Diagnostics, Reports | v0.5.0 | **Done** (`docs/status/m4-storage-diagnostics-reports.md`) |
| M5 — MVP Hardening & Release | v1.0.0 | Next |

## M0 — Skeleton & Rails

*Objective:* empty-but-running app plus all rails: repo layout, Meson build, CI (both lanes),
lint/mypy/import-linter, window with sidebar and one placeholder page, logging, `./run` +
`./check` — plus a stack-validation spike proving GTK4 + libadwaita + Blueprint +
PyGObject-asyncio (or executor fallback) + Meson + dbusmock on each supported Ubuntu LTS.
*Acceptance:* `./run` opens a window and `./check` passes on both LTS releases; async
mechanism per LTS recorded in ADR-0007; CI green. Docs: contracts only — guides are extracted
from real code at end of M1.

## M1 — System Overview & Hardware Information

*Objective:* Dashboard page (model, BIOS version, kernel, uptime, quick stats) + Hardware
page (DMI identity, CPU/memory summary, PCI/USB inventory). Providers: `dmi`, `os_info`,
`pci_usb`, `thinkpad_acpi` (detection only). Graceful banner on non-ThinkPads.
*Acceptance:* correct data on 2+ real ThinkPads, which must include the **ThinkPad E16
Gen 2** (the maintainer's machine and the project's primary reference hardware — see
`docs/testing.md`); every panel handles `unavailable`; fixture governance (schema,
capture-time redaction, review checklist) in place before the first community capture. *Docs:* module docs for shipped providers; `docs/guides/` recipes
extracted from the real code.

## M2 — Battery Health & Wear Analysis

*Objective:* Battery page — live status via UPower, wear analysis via sysfs
(`charge_full[_design]`, `cycle_count`), health classification, daily snapshot history +
wear-over-time chart, dual-battery support.
*Acceptance:* wear % matches manual sysfs math; missing `cycle_count` handled; history
survives restarts. Close = **public alpha** — all open-source hygiene files must exist
(done in M0).

## M3 — Firmware Updates (fwupd/LVFS)

*Objective:* Firmware page — device list, versions, release notes, metadata refresh, updates
via fwupd D-Bus (its polkit governs), reboot-required and progress states.
*Acceptance:* full update flow verified on real hardware against LVFS; failure paths render
correctly. UX criteria: unambiguous reboot flow; failure recovery path; AC/battery
preconditions surfaced before commit; post-update "what changed"; declined auth is silent.
Close = **beta**.

## M4 — Storage Health, Diagnostics & Report Export

*Entry gate:* **ADR-0006 accepted** (helper threat model); SECURITY.md published (done, M0).
*Objective:* privileged helper + polkit policy; Storage page (SMART/NVMe); diagnostics engine
+ initial checks (battery wear, SMART, firmware currency, thermal sanity, disk space); health
score on Dashboard (per-signal confidence, labeled experimental); report export (MD/HTML/JSON)
redacted by default.
*Acceptance:* SMART data after one polkit prompt; declining degrades gracefully; diagnostics
< 10 s; helper negative/injection suite passes.

## M5 — MVP Hardening & Release (v1.0)

*Objective:* polish, perf, PPA pipeline, user docs, community hardware-test round across ≥ 5
ThinkPad models; health-score calibration review.
*Acceptance:* MVP definition below fully met; zero known crashers; install-from-PPA works on
both LTS. Accessibility: full keyboard navigation, screen-reader labels on all rows, no
information by color alone, respects font scaling. Performance: < 1.5 s launch → window +
first meaningful dashboard content on a mid-range ThinkPad.

## MVP Definition (the 1.0 bar)

A user on Ubuntu LTS with a ThinkPad installs Lapcare from a PPA and can: (1) see system
overview and full hardware info with no terminal or prompts; (2) see battery status, health
classification, wear %, cycle count, and wear history; (3) see, refresh, and install firmware
updates with correct progress/reboot flows; (4) see storage SMART/NVMe health after a single
polkit auth; (5) run one-click diagnostics with an explainable, confidence-marked health
dashboard; (6) export a redacted-by-default diagnostic report; (7) every feature degrades
gracefully on missing tools, unsupported hardware, or denied auth.

**Not in MVP:** hardware writes (charge thresholds, always-on USB), thermal/fan live pages,
notifications, scheduling, tray/background presence, non-ThinkPad guarantees, Flatpak.

## Post-1.0 (order tentative)

- **M6 — Battery charge thresholds:** first write; new polkit action; triggers the deferred
  ADRs on the privileged D-Bus service (ADR-0004) and the capability model (ADR-0008).
- **M7 — Thermal & fan monitoring:** hwmon live charts; thinkpad_acpi fan RPM (fan *control*
  much later, if ever — safety-sensitive).
- **M8 — Notifications & scheduling:** XDG Notification portal; systemd user timers (no
  in-app daemon).
- **M9 — ThinkPad extras:** always-on USB, keyboard backlight, privacy states — each with its
  own polkit action if it writes.
- **M10 — Broader hardware:** vendor quirk layers (Framework, Dell); capability-model ADR if
  M6 hasn't forced it; rename/rebrand decision.
- **M11 — Flatpak**, once the D-Bus service architecture makes sandboxing honest (ADR-0005).

## Appendix: planned provider → transport map

| Provider | Source | Transport | Privilege |
|---|---|---|---|
| `upower` | Battery/AC state | D-Bus `org.freedesktop.UPower` | none |
| `battery_sysfs` | Wear: `charge_full[_design]`, `cycle_count` | `/sys/class/power_supply/BAT*/` | none |
| `fwupd` | Firmware devices/releases/updates | D-Bus `org.freedesktop.fwupd` | fwupd's polkit |
| `dmi` | Model, serial, BIOS | `/sys/class/dmi/id/`; root-only fields via helper | mostly none |
| `thinkpad_acpi` | ThinkPad detection, fan, LEDs | `/sys/devices/platform/thinkpad_acpi/`, `/proc/acpi/ibm/` | none (read) |
| `hwmon` | Temperatures, fan RPM | `/sys/class/hwmon/` | none |
| `storage_smart` | SMART/NVMe health | `smartctl --json` / `nvme --output-format=json` via helper | polkit |
| `pci_usb` | Device inventory | `lspci -mm`, `lsusb` or sysfs walk | none |
| `os_info` | Kernel, distro, uptime | `/etc/os-release`, `/proc` | none |
