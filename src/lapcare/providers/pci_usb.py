# SPDX-License-Identifier: GPL-3.0-or-later
"""pci_usb provider: device inventory via ``lspci -mm`` and ``lsusb``.

Implements core.ports.DeviceInventoryProvider. Concrete class PciUsbTools.
Both commands run through the audited runner (injectable for fixtures).

Formats owned here and nowhere else:
- ``lspci -mm``: one device per line —
  ``00:02.0 "VGA compatible controller" "Intel Corporation" "Device 7d55"
  -r08 "Lenovo" "Device 50e1"`` —
  slot, then quoted class/vendor/device (then optional -rXX/-pXX and
  subsystem strings we ignore). Parsed with shlex; malformed lines are
  skipped with a DEBUG log — a truncated pci.ids database yields
  "Device XXXX" names, which are data, not errors.
- ``lsusb``: ``Bus 003 Device 002: ID 27c6:659a Shenzhen Goodix ...`` —
  root hubs (1d6b:*) are real devices and included; the UI may filter.

Error mapping (STYLEGUIDE): ToolNotFound → ProviderUnavailable(TOOL_MISSING,
tool=package name); ToolTimeout → ProviderTimeout; ToolFailed/zero-parse →
ProviderParseError. Raw output is logged at DEBUG only.
"""

from __future__ import annotations

import logging
import os
import re
import shlex

from lapcare.core.errors import ProviderParseError, ProviderTimeout, ProviderUnavailable
from lapcare.core.models import Availability, PciDevice, UsbDevice
from lapcare.platform.subprocess import (
    ALLOWED_TOOLS,
    ToolFailed,
    ToolNotFound,
    ToolRunner,
    ToolTimeout,
    run_tool,
)

log = logging.getLogger(__name__)

SOURCE = "pci_usb"
_PACKAGES = {"lspci": "pciutils", "lsusb": "usbutils"}
_USB_LINE = re.compile(
    r"^Bus (?P<bus>\d+) Device (?P<dev>\d+): "
    r"ID (?P<vid>[0-9a-fA-F]{4}):(?P<pid>[0-9a-fA-F]{4})\s*(?P<name>.*)$"
)


class PciUsbTools:
    def __init__(self, runner: ToolRunner = run_tool) -> None:
        self._run = runner

    def availability(self) -> Availability:
        for tool in ("lspci", "lsusb"):
            if any(os.access(c, os.X_OK) for c in ALLOWED_TOOLS[tool]):
                return Availability.OK
        return Availability.TOOL_MISSING

    async def _run_translated(self, tool: str, args: list[str]) -> str:
        try:
            return await self._run(tool, args)
        except ToolNotFound as exc:
            raise ProviderUnavailable(
                SOURCE, Availability.TOOL_MISSING, tool=_PACKAGES[tool]
            ) from exc
        except ToolTimeout as exc:
            raise ProviderTimeout(SOURCE, str(exc)) from exc
        except ToolFailed as exc:
            raise ProviderParseError(SOURCE, f"{tool} exited {exc.returncode}") from exc

    async def list_pci(self) -> list[PciDevice]:
        out = await self._run_translated("lspci", ["-mm"])
        devices: list[PciDevice] = []
        for line in out.splitlines():
            if not line.strip():
                continue
            try:
                tokens = shlex.split(line)
            except ValueError:
                log.debug("unparseable lspci line: %.120r", line)
                continue
            fields = [t for t in tokens[1:] if not t.startswith("-")]
            if not tokens or len(fields) < 3:
                log.debug("short lspci line: %.120r", line)
                continue
            devices.append(
                PciDevice(
                    slot=tokens[0],
                    device_class=fields[0],
                    vendor=fields[1],
                    device=fields[2],
                )
            )
        if not devices and out.strip():
            raise ProviderParseError(SOURCE, "lspci output had no parseable lines")
        return devices

    async def list_usb(self) -> list[UsbDevice]:
        out = await self._run_translated("lsusb", [])
        devices: list[UsbDevice] = []
        for line in out.splitlines():
            if not line.strip():
                continue
            match = _USB_LINE.match(line.strip())
            if match is None:
                log.debug("unparseable lsusb line: %.120r", line)
                continue
            devices.append(
                UsbDevice(
                    bus=match["bus"],
                    device=match["dev"],
                    vendor_id=match["vid"].lower(),
                    product_id=match["pid"].lower(),
                    name=match["name"].strip() or None,
                )
            )
        if not devices and out.strip():
            raise ProviderParseError(SOURCE, "lsusb output had no parseable lines")
        return devices
