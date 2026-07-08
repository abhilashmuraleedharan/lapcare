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

## battery_sysfs (`BatterySysfs`) — implements BatteryWearProvider

Walks `/sys/class/power_supply/*`, filters `type == Battery`; reads unit family
(energy_*/charge_*), cycle_count, model/manufacturer/technology. Never reads
`serial_number`.

| Quirk | Evidence |
|---|---|
| E16 Gen 2 reports **energy_*** (µWh); other machines report charge_* (µAh) — both real, energy preferred when both | E16 fixture vs synthetic-charge-units |
| `ucsi-source-psy-USBC*` power-supply entries exist and must be type-filtered | E16 live probe |
| `status` can be `"Not charging"` on AC below the charge threshold — a distinct state, not an error | E16 at 79% |
| Some EC firmware reports cycle_count -1 (or 0) → normalize to None | synthetic-pathological BAT1 |
| Fresh/recalibrated packs report full above design → analysis clamps wear at 0 | synthetic-pathological BAT0 |
| `power_now` is 0 when not charging → no time estimates | E16 live probe |

## upower (`UPowerDbus`) — implements BatteryStatusProvider

D-Bus `org.freedesktop.UPower`: EnumerateDevices + per-device Properties.GetAll;
Type==2 && PowerSupply filter; change signals coalesced to `on_change` on the
GTK main thread (subscribe from the main thread only — see platform/dbus.py).

| Quirk | Evidence |
|---|---|
| TimeToEmpty/TimeToFull of 0 mean "unknown" → None | UPower semantics; dbusmock tests |
| Pending-charge/discharge states map to NOT_CHARGING (threshold ThinkPads) | state map |
| No system bus (containers/CI) → ProviderUnavailable(TOOL_MISSING, upower); consumers must treat live status as optional | container validation |

## pci_usb (`PciUsbTools`) — implements DeviceInventoryProvider

Runs `lspci -mm` and `lsusb` (packages: pciutils, usbutils) via the audited runner.

| Quirk | Evidence |
|---|---|
| New silicon shows `Device XXXX` names until pci.ids catches up — that's data, not an error | E16 Gen 2 capture (Meteor Lake) |
| lsusb includes root hubs (`1d6b:*`) — real devices; UI may filter later | E16 capture: 7 devices incl. hubs |
| lspci `-r`/`-p` revision tokens are skipped in parsing | parser |
| Cloud/CI VMs can have NO USB subsystem — lsusb exits nonzero ("unable to initialize usb spec"). Consumers must degrade per-panel, not per-page | GitHub Actions runner, 2026-07 |

## fwupd (`FwupdGir`) — implements FirmwareProvider

`gi.repository.Fwupd` (`Fwupd.Client`) over the system bus — libfwupd, not raw D-Bus
calls, so download/signature-verify/fd-passing stay fwupd's code (ADR-0009). Change and
progress signals and daemon battery properties DO use raw GDBus (subscriptions +
`Properties.GetAll`) — see the module docstring and ADR-0009 for why the client's own
GObject signals and cached getters can't be used. Local dbusmock template:
`tests/dbusmock_templates/fwupd.py` (upstream ships none).

| Quirk | Evidence |
|---|---|
| **Every `Fwupd.Client` needs `set_main_context()` with a persistent context** — the sync helpers otherwise free the per-call context the internal proxy stays bound to; the next daemon signal crashes the process. Use `providers/fwupd.py:_new_client()` only | measured; upstream `fwupd-client-sync.c` |
| `GetUpgrades` raises `NothingToDo`/`NotFound` for "no newer release" → empty list (data, not unavailability) | E16 Gen 2 live probe (KEK CA devices) |
| Devices can report `version=None` (CPU microcode, UEFI KEK) and duplicate display names ("UEFI Device Firmware" ×8 on the E16) | E16 Gen 2 live probe, 20 devices |
| `BatteryLevel`/`BatteryThreshold` sentinel **101 = unknown** → None; real E16 values 62%/25% | E16 live probe |
| `Percentage = 0` means unknown (per upstream D-Bus doc) → None in progress callbacks | `src/org.freedesktop.fwupd.xml` |
| `refresh_remote()` downloads metadata **in-process over HTTPS** (only `UpdateMetadata` goes to the daemon); only ENABLED+DOWNLOAD remotes are refreshable | upstream `fwupd-client.c`; ADR-0009 |
| Device IDs are 40-char sha1 hex; libfwupd hard-asserts the format (`fwupd_device_id_is_valid`) — never invent IDs in tests | dbusmock template development |
| No fwupd daemon (containers/CI) or AppArmor-denied bus → ProviderUnavailable(TOOL_MISSING, fwupd) | container validation |
