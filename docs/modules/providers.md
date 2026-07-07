# Module: providers

One adapter per data source; each owns ALL knowledge of its source's quirks. Interfaces
in `core/ports.py`; recipe in `docs/guides/adding-a-provider.md`. Fixture-verified quirks
are recorded here — this file is the project's institutional memory about hardware.

## dmi (`DmiSysfs`) — implements SystemIdentityProvider

Reads `/sys/class/dmi/id/{sys_vendor, product_name, product_family, product_version,
board_name, bios_version, bios_date, product_serial}`.

| Quirk | Evidence |
|---|---|
| ThinkPads put the machine type in `product_name` (e.g. `21MBCTO1WW`) and the marketing name in `product_family`/`product_version` | E16 Gen 2 fixture |
| BIOS version strings can contain internal whitespace — display verbatim | `R2JET48W(1.25 )` on E16 Gen 2 |
| `product_serial` is root-only (0400) → None unprivileged, by design | all machines so far |
| VMs expose few fields (`QEMU` vendor, no family) | qemu-vm fixture |
| Some ARM machines have no DMI directory at all → UNSUPPORTED_HARDWARE | untested; fixture wanted |

## os_info (`OsInfoProc`) — implements OsInfoProvider

Reads `/etc/os-release`, `/proc/uptime`, `/proc/sys/kernel/{osrelease,hostname}`,
`/proc/cpuinfo`, `/proc/meminfo`.

| Quirk | Evidence |
|---|---|
| os-release fields are optional by spec; parser tolerates junk lines | synthetic-sparse fixture |
| ARM cpuinfo lacks `model name` → cpu_model None | documented; fixture wanted (X13s) |
| `cpu_count` is LOGICAL processors (cpuinfo `processor` entries) | — |

## thinkpad_acpi (`ThinkpadAcpiSysfs`) — implements ThinkpadProvider

Detection only (M1): `/sys/devices/platform/thinkpad_acpi` existence + DMI cross-check via
the SystemIdentityProvider port. Either signal suffices.

| Quirk | Evidence |
|---|---|
| E16 Gen 2 exposes fan/thermal/kbdlight/led attributes (future M7/M9 surface) | attribute listing in fixture |
| E-series driver surface may differ from T/X-series — never assume | docs/testing.md rule |

## pci_usb (`PciUsbTools`) — implements DeviceInventoryProvider

Runs `lspci -mm` and `lsusb` (packages: pciutils, usbutils) via the audited runner.

| Quirk | Evidence |
|---|---|
| New silicon shows `Device XXXX` names until pci.ids catches up — that's data, not an error | E16 Gen 2 capture (Meteor Lake) |
| lsusb includes root hubs (`1d6b:*`) — real devices; UI may filter later | E16 capture: 7 devices incl. hubs |
| lspci `-r`/`-p` revision tokens are skipped in parsing | parser |
| Cloud/CI VMs can have NO USB subsystem — lsusb exits nonzero ("unable to initialize usb spec"). Consumers must degrade per-panel, not per-page | GitHub Actions runner, 2026-07 |
