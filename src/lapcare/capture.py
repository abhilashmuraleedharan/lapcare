# SPDX-License-Identifier: GPL-3.0-or-later
"""Fixture capture: ``lapcare --capture-fixtures [DIR]``.

Captures this machine's provider data into the ``<source>/<machine>/``
layout used by ``tests/fixtures/`` so a bug report can become a regression
fixture. Headless — never imports GTK.

Privacy (constitution invariant #5): identifiers are redacted AT CAPTURE
TIME by default — DMI serial/UUID/asset files are not captured at all, and
the hostname is replaced with ``redacted-host``. ``--include-identifiers``
exists for local debugging only; such captures are never accepted upstream
(review checklist in docs/testing.md).
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import re
from pathlib import Path

from lapcare import __version__
from lapcare.platform.files import read_str
from lapcare.platform.subprocess import ToolRunner, run_tool

log = logging.getLogger(__name__)

# Capture manifests: exactly the files the providers document reading.
_DMI_DIR = "sys/class/dmi/id"
_DMI_FILES = (
    "sys_vendor",
    "product_name",
    "product_family",
    "product_version",
    "board_name",
    "bios_version",
    "bios_date",
)
_DMI_IDENTIFIER_FILES = (
    "product_serial",
    "product_uuid",
    "board_serial",
    "chassis_serial",
    "board_asset_tag",
    "chassis_asset_tag",
)
_OS_INFO_FILES = (
    "etc/os-release",
    "proc/uptime",
    "proc/sys/kernel/osrelease",
    "proc/cpuinfo",
    "proc/meminfo",
)
_HOSTNAME_FILE = "proc/sys/kernel/hostname"
_TP_ACPI_DIR = "sys/devices/platform/thinkpad_acpi"
_POWER_SUPPLY_DIR = "sys/class/power_supply"
# serial_number deliberately absent (identifier — never captured by default).
_POWER_SUPPLY_FILES = (
    "type",
    "status",
    "online",
    "capacity",
    "cycle_count",
    "energy_full",
    "energy_full_design",
    "energy_now",
    "charge_full",
    "charge_full_design",
    "charge_now",
    "power_now",
    "model_name",
    "manufacturer",
    "technology",
    "present",
    "voltage_min_design",
)


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "unknown-machine"


def _copy_file(root: Path, relpath: str, dest_root: Path) -> bool:
    content = read_str(root / relpath)
    if content is None:
        return False
    target = dest_root / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content + "\n")
    return True


async def capture(
    out: Path,
    root: Path = Path("/"),
    runner: ToolRunner = run_tool,
    include_identifiers: bool = False,
) -> str:
    """Capture all sources into ``out``; return the machine slug directory name."""
    family = read_str(root / _DMI_DIR / "product_family") or read_str(
        root / _DMI_DIR / "product_name"
    )
    machine = _slug(family or "")
    notes: list[str] = []

    # dmi
    dmi_dest = out / "dmi" / machine
    for name in _DMI_FILES:
        _copy_file(root, f"{_DMI_DIR}/{name}", dmi_dest)
    if include_identifiers:
        for name in _DMI_IDENTIFIER_FILES:
            _copy_file(root, f"{_DMI_DIR}/{name}", dmi_dest)
        notes.append("IDENTIFIERS INCLUDED — local debugging only, never share")
    else:
        notes.append("identifiers redacted at capture time (default)")

    # os_info
    os_dest = out / "os_info" / machine
    for relpath in _OS_INFO_FILES:
        _copy_file(root, relpath, os_dest)
    hostname_target = os_dest / _HOSTNAME_FILE
    hostname_target.parent.mkdir(parents=True, exist_ok=True)
    if include_identifiers:
        _copy_file(root, _HOSTNAME_FILE, os_dest)
    else:
        hostname_target.write_text("redacted-host\n")

    # thinkpad_acpi: uevent + attribute name listing (names only, no values)
    tp_dir = root / _TP_ACPI_DIR
    if tp_dir.is_dir():
        tp_dest = out / "thinkpad_acpi" / machine
        _copy_file(root, f"{_TP_ACPI_DIR}/uevent", tp_dest)
        listing = sorted(p.name for p in tp_dir.iterdir())
        target = tp_dest / _TP_ACPI_DIR / "attribute-names.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(listing) + "\n")
    else:
        notes.append("thinkpad_acpi driver not present on this machine")

    # battery_sysfs: every power-supply entry, manifest files only
    ps_dir = root / _POWER_SUPPLY_DIR
    if ps_dir.is_dir():
        bat_dest = out / "battery_sysfs" / machine
        for entry in sorted(ps_dir.iterdir()):
            for name in _POWER_SUPPLY_FILES:
                _copy_file(root, f"{_POWER_SUPPLY_DIR}/{entry.name}/{name}", bat_dest)

    # pci_usb via the audited runner
    pu_dest = out / "pci_usb" / machine
    pu_dest.mkdir(parents=True, exist_ok=True)
    for tool, args in (("lspci", ["-mm"]), ("lsusb", [])):
        try:
            output = await runner(tool, args)
        except Exception as exc:  # tool missing/failed: note it, keep capturing
            notes.append(f"{tool}: not captured ({exc})")
            continue
        (pu_dest / f"{tool}.txt").write_text(output)

    stamp = datetime.datetime.now(tz=datetime.UTC).strftime("%Y-%m-%d")
    kernel = read_str(root / "proc/sys/kernel/osrelease") or "unknown"
    (out / "README.md").write_text(
        f"# Lapcare fixture capture\n\n"
        f"- machine: {machine}\n"
        f"- captured: {stamp} (lapcare {__version__})\n"
        f"- kernel: {kernel}\n"
        + "".join(f"- note: {n}\n" for n in notes)
        + "\nLayout: `<source>/<machine>/...` — drop directories into"
        " `tests/fixtures/` (see docs/testing.md for the review checklist).\n"
    )
    return machine


def run_capture(out: Path, include_identifiers: bool = False) -> int:
    """Synchronous CLI entry used by app.main. Returns an exit code."""
    machine = asyncio.run(capture(out, include_identifiers=include_identifiers))
    log.info("fixtures captured machine=%s dir=%s", machine, out)
    print(f"Captured fixtures for '{machine}' into {out}/")
    if include_identifiers:
        print("WARNING: identifiers included — do NOT attach this capture to public issues.")
    return 0
