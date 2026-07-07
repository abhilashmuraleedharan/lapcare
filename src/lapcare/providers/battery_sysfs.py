# SPDX-License-Identifier: GPL-3.0-or-later
"""battery_sysfs provider: static/wear battery data from /sys/class/power_supply.

Implements core.ports.BatteryWearProvider. Concrete class BatterySysfs.

Walks ``/sys/class/power_supply/*`` and keeps entries whose ``type`` file
says ``Battery`` — this filters AC adapters and the ``ucsi-source-psy-*``
USB-C source entries seen on the E16 Gen 2. Per battery it reads:

- Unit family (drivers vary; both are real):
  ``energy_full`` / ``energy_full_design`` (µWh) — E16 Gen 2 reports these —
  or ``charge_full`` / ``charge_full_design`` (µAh). Energy is preferred
  when both families are present.
- ``cycle_count`` — absent on some models; some EC firmware reports -1 or 0,
  normalized to None (quirk registry).
- ``model_name``, ``manufacturer``, ``technology``.

``serial_number`` exists in sysfs but is deliberately never read (privacy
invariant). Empty result = no batteries (desktop) = data, not an error.
"""

from __future__ import annotations

import logging
from pathlib import Path

from lapcare.core.models import Availability, BatteryWear, CapacityUnit
from lapcare.platform.files import read_int, read_str

log = logging.getLogger(__name__)

SOURCE = "battery_sysfs"
_PS_DIR = "sys/class/power_supply"


def _read_capacity(entry: Path) -> tuple[int | None, int | None, CapacityUnit | None]:
    energy_full = read_int(entry / "energy_full")
    energy_design = read_int(entry / "energy_full_design")
    if energy_full is not None or energy_design is not None:
        return energy_full, energy_design, CapacityUnit.MICRO_WATT_HOURS
    charge_full = read_int(entry / "charge_full")
    charge_design = read_int(entry / "charge_full_design")
    if charge_full is not None or charge_design is not None:
        return charge_full, charge_design, CapacityUnit.MICRO_AMP_HOURS
    return None, None, None


class BatterySysfs:
    def __init__(self, root: Path = Path("/")) -> None:
        self._ps = root / _PS_DIR

    def availability(self) -> Availability:
        if self._ps.is_dir():
            return Availability.OK
        return Availability.UNSUPPORTED_HARDWARE

    async def list_batteries(self) -> list[BatteryWear]:
        if not self._ps.is_dir():
            return []
        batteries: list[BatteryWear] = []
        for entry in sorted(self._ps.iterdir()):
            if read_str(entry / "type", max_bytes=64) != "Battery":
                continue
            full, design, unit = _read_capacity(entry)
            cycle_count = read_int(entry / "cycle_count")
            if cycle_count is not None and cycle_count <= 0:
                # Some EC firmware reports -1 (or 0 while genuinely cycled).
                log.debug("%s: cycle_count %d normalized to None", entry.name, cycle_count)
                cycle_count = None
            batteries.append(
                BatteryWear(
                    name=entry.name,
                    capacity_full=full,
                    capacity_design=design,
                    capacity_unit=unit,
                    cycle_count=cycle_count,
                    model_name=read_str(entry / "model_name", max_bytes=256),
                    manufacturer=read_str(entry / "manufacturer", max_bytes=256),
                    technology=read_str(entry / "technology", max_bytes=64),
                )
            )
        log.debug("found %d batteries", len(batteries))
        return batteries
