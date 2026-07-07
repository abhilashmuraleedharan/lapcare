# SPDX-License-Identifier: GPL-3.0-or-later
"""dmi provider: system identity from /sys/class/dmi/id (SMBIOS/DMI).

Implements core.ports.SystemIdentityProvider. Concrete class DmiSysfs.

Files read (each a single stripped line; all Optional):
- ``sys_vendor``       "LENOVO" on ThinkPads
- ``product_name``     machine type model, e.g. "21MBCTO1WW"
- ``product_family``   marketing name, e.g. "ThinkPad E16 Gen 2"
- ``product_version``  usually mirrors product_family on ThinkPads
- ``board_name``       often equals product_name on ThinkPads
- ``bios_version``     e.g. "R2JET48W(1.25 )" — embedded trailing space is real
- ``bios_date``        MM/DD/YYYY as firmware reports it
- ``product_serial``   root-only (0400) on most machines → None unprivileged,
                       by design; the M4 helper's dmi-full verb reads it

Stability notes / quirks (fixture-verified where possible):
- Reference values above captured from the maintainer's E16 Gen 2 (2026-07).
- Non-Lenovo and VM machines populate these differently (QEMU puts "QEMU" in
  sys_vendor); some ARM machines have no DMI at all → UNSUPPORTED_HARDWARE.
- Never parse `dmidecode` output here — this provider is sysfs-only.
"""

from __future__ import annotations

import logging
from pathlib import Path

from lapcare.core.models import Availability, SystemIdentity
from lapcare.platform.files import read_str

log = logging.getLogger(__name__)

SOURCE = "dmi"
_DMI_DIR = "sys/class/dmi/id"


class DmiSysfs:
    def __init__(self, root: Path = Path("/")) -> None:
        self._dmi = root / _DMI_DIR

    def availability(self) -> Availability:
        if self._dmi.is_dir():
            return Availability.OK
        return Availability.UNSUPPORTED_HARDWARE

    async def read_identity(self) -> SystemIdentity:
        def field(name: str) -> str | None:
            return read_str(self._dmi / name, max_bytes=4096)

        return SystemIdentity(
            vendor=field("sys_vendor"),
            product_name=field("product_name"),
            product_family=field("product_family"),
            product_version=field("product_version"),
            board_name=field("board_name"),
            bios_version=field("bios_version"),
            bios_date=field("bios_date"),
            serial=field("product_serial"),
        )
