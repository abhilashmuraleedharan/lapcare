# SPDX-License-Identifier: GPL-3.0-or-later
"""thinkpad_acpi provider: ThinkPad detection. M1 scope is DETECTION ONLY —
fan/thermal/LED surfaces of this driver are M7+/M9 milestones.

Implements core.ports.ThinkpadProvider. Concrete class ThinkpadAcpiSysfs.

Signals combined (either suffices — belt and braces because both lie
occasionally on old/odd firmware):
- ``/sys/devices/platform/thinkpad_acpi`` directory exists → the kernel
  driver bound to this machine (strongest signal).
- DMI says vendor LENOVO and product family/version contains "ThinkPad" —
  obtained via the SystemIdentityProvider PORT, never by parsing DMI files
  here (provider isolation: dmi quirks live in providers.dmi).

Reference: maintainer's E16 Gen 2 has the driver loaded with a rich attribute
surface (fan, thermal, kbdlight, led — see docs/status/m1 probe notes).
"""

from __future__ import annotations

import logging
from pathlib import Path

from lapcare.core.models import Availability, ThinkpadInfo
from lapcare.core.ports import SystemIdentityProvider

log = logging.getLogger(__name__)

SOURCE = "thinkpad_acpi"
_DRIVER_DIR = "sys/devices/platform/thinkpad_acpi"


class ThinkpadAcpiSysfs:
    def __init__(
        self,
        root: Path = Path("/"),
        identity: SystemIdentityProvider | None = None,
    ) -> None:
        self._root = root
        self._identity = identity

    def availability(self) -> Availability:
        # Detection itself always works where sysfs exists; "not a ThinkPad"
        # is a RESULT (data), not unavailability.
        if (self._root / "sys").is_dir():
            return Availability.OK
        return Availability.UNSUPPORTED_HARDWARE

    async def detect(self) -> ThinkpadInfo:
        driver_loaded = (self._root / _DRIVER_DIR).is_dir()

        vendor_lenovo = False
        model: str | None = None
        if self._identity is not None:
            ident = await self._identity.read_identity()
            vendor_lenovo = (ident.vendor or "").strip().upper() == "LENOVO"
            for candidate in (ident.product_family, ident.product_version):
                if candidate and "thinkpad" in candidate.lower():
                    model = candidate
                    break

        is_thinkpad = driver_loaded or (vendor_lenovo and model is not None)
        log.debug(
            "detect: driver=%s lenovo=%s model=%s -> thinkpad=%s",
            driver_loaded,
            vendor_lenovo,
            model,
            is_thinkpad,
        )
        return ThinkpadInfo(
            is_thinkpad=is_thinkpad,
            dmi_vendor_lenovo=vendor_lenovo,
            acpi_driver_loaded=driver_loaded,
            model=model,
        )
