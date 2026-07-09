# SPDX-License-Identifier: GPL-3.0-or-later
"""hwmon provider: temperature sensors via /sys/class/hwmon.

Implements core.ports.ThermalProvider. Concrete class HwmonSysfs.

Reads, per ``/sys/class/hwmon/hwmon<N>/``:
- ``name``            — chip name, e.g. "thinkpad", "coretemp", "nvme", "acpitz"
- ``temp<M>_input``   — millidegrees Celsius (integer)
- ``temp<M>_label``   — optional human label ("CPU", "Package id 0")

Quirks (docs/modules/providers.md#hwmon, all measured on the E16 Gen 2):
- The thinkpad EC chip exposes 8 temp slots regardless of population:
  unpopulated slots read implausible values (2 °C, 12-13 °C) or fail the
  read outright (temp8_input returns an error). The provider returns what
  the kernel returns — plausibility is the diagnostics engine's policy
  (core.diagnostics PLAUSIBLE_* bounds), not a parse decision.
- Slot numbering is not contiguous (coretemp jumps temp10 → temp14).

Absence of hwmon entirely (rare) is an empty list — data, not an error.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from lapcare.core.models import Availability, TemperatureReading
from lapcare.platform.files import read_int, read_str

log = logging.getLogger(__name__)

SOURCE = "hwmon"
_TEMP_INPUT = re.compile(r"^temp(\d+)_input$")


class HwmonSysfs:
    def __init__(self, root: Path = Path("/")) -> None:
        self._root = root

    def availability(self) -> Availability:
        if (self._root / "sys/class/hwmon").is_dir():
            return Availability.OK
        return Availability.UNSUPPORTED_HARDWARE

    async def list_temperatures(self) -> list[TemperatureReading]:
        base = self._root / "sys/class/hwmon"
        readings: list[TemperatureReading] = []
        try:
            chips = sorted(base.iterdir())
        except OSError as exc:
            log.debug("hwmon unreadable: %s", exc)
            return readings
        for chip_dir in chips:
            chip = read_str(chip_dir / "name") or chip_dir.name
            try:
                entries = sorted(p.name for p in chip_dir.iterdir())
            except OSError:
                continue
            for entry in entries:
                match = _TEMP_INPUT.match(entry)
                if match is None:
                    continue
                milli = read_int(chip_dir / entry)
                if milli is None:  # unpopulated slot (E16 EC temp8): skip
                    continue
                label = read_str(chip_dir / f"temp{match.group(1)}_label")
                readings.append(TemperatureReading(chip=chip, label=label, celsius=milli / 1000.0))
        return readings
