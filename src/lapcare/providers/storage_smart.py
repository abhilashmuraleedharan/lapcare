# SPDX-License-Identifier: GPL-3.0-or-later
"""storage_smart provider: /sys/block inventory + SMART via the ADR-0006 helper.

Implements core.ports.StorageProvider. Concrete class StorageSmartPkexec.

Unprivileged surface (never prompts), read via platform.files:
- ``/sys/block/<name>/`` — a block device exists; entries WITHOUT a
  ``device/`` subdirectory are virtual (loop, zram, dm-*, md) and skipped.
- ``/sys/block/<name>/size`` — 512-byte sectors, universal.
- ``/sys/block/<name>/removable``, ``/sys/block/<name>/queue/rotational``.
- ``/sys/block/<name>/device/model`` — NVMe exposes it on the controller
  device this symlink reaches; SATA pads with spaces (stripped by read_str).

Privileged surface (ADR-0006; one polkit prompt, ``auth_admin_keep``):
- ``pkexec /usr/libexec/lapcare/lapcare-helper smart-report <name>`` →
  verbatim ``smartctl --json --all /dev/<name>``. 120 s timeout — the run
  CONTAINS the interactive auth prompt (§15).

Error mapping: pkexec exits 126 (dialog dismissed) / 127 (not authorized)
→ PrivilegedActionDenied; any other failure carries the helper's
machine-readable stderr line (``lapcare-helper: <code>[: detail]``, §13):
tool-missing → ProviderUnavailable(TOOL_MISSING, tool="smartmontools"),
tool-timeout → ProviderTimeout, everything else → ProviderParseError.
A missing pkexec or helper binary → ProviderUnavailable(TOOL_MISSING) with
the missing piece named (dev builds run uninstalled — expected there).

Quirks (docs/modules/providers.md#storage_smart):
- E16 Gen 2 SK hynix NVMe: no self-test log → smartctl sets exit bit 2 with
  full, healthy JSON; the helper passes it through (ADR-0006 §12) and the
  failure string appears in ``SmartReport.messages`` as a data-quality note.
- ``serial_number`` is an identifier (§17): own field, never logged above
  DEBUG, excluded from exports by default.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from lapcare.core.errors import (
    PrivilegedActionDenied,
    ProviderParseError,
    ProviderTimeout,
    ProviderUnavailable,
)
from lapcare.core.models import Availability, SmartReport, StorageDevice
from lapcare.platform.files import read_int, read_str
from lapcare.platform.subprocess import (
    ToolFailed,
    ToolNotFound,
    ToolRunner,
    ToolTimeout,
    run_tool,
)

log = logging.getLogger(__name__)

SOURCE = "storage_smart"
HELPER_PATH = "/usr/libexec/lapcare/lapcare-helper"
ACTION_SMART_REPORT = "io.github.abhilashmuraleedharan.lapcare.smart-report"
# The pkexec run contains a human typing a password (ADR-0006 §15).
_PKEXEC_TIMEOUT_S = 120.0
_PKEXEC_DISMISSED = 126
_PKEXEC_NOT_AUTHORIZED = 127


def _flag(value: int | None) -> bool | None:
    return None if value is None else bool(value)


class StorageSmartPkexec:
    def __init__(self, root: Path = Path("/"), runner: ToolRunner = run_tool) -> None:
        self._root = root
        self._run = runner

    def availability(self) -> Availability:
        if (self._root / "sys/block").is_dir():
            return Availability.OK
        return Availability.UNSUPPORTED_HARDWARE

    # -- unprivileged inventory ------------------------------------------------

    async def list_devices(self) -> list[StorageDevice]:
        base = self._root / "sys/block"
        try:
            names = sorted(os.listdir(base))
        except OSError as exc:
            raise ProviderUnavailable(SOURCE, Availability.UNSUPPORTED_HARDWARE) from exc
        devices: list[StorageDevice] = []
        for name in names:
            entry = base / name
            if not (entry / "device").is_dir():  # virtual: loop, zram, dm-*
                continue
            sectors = read_int(entry / "size")
            devices.append(
                StorageDevice(
                    name=name,
                    model=read_str(entry / "device/model"),
                    size_bytes=None if sectors is None else sectors * 512,
                    removable=_flag(read_int(entry / "removable")),
                    rotational=_flag(read_int(entry / "queue/rotational")),
                )
            )
        return devices  # empty list = no physical disks (data, not an error)

    # -- privileged SMART read (ADR-0006) --------------------------------------

    async def read_smart(self, device_name: str) -> SmartReport:
        try:
            out = await self._run(
                "pkexec",
                [HELPER_PATH, "smart-report", device_name],
                timeout=_PKEXEC_TIMEOUT_S,
            )
        except ToolNotFound as exc:
            raise ProviderUnavailable(SOURCE, Availability.TOOL_MISSING, tool="pkexec") from exc
        except ToolTimeout as exc:
            raise ProviderTimeout(SOURCE, str(exc)) from exc
        except ToolFailed as exc:
            raise self._translate_failure(exc) from exc
        try:
            data = json.loads(out)
        except ValueError as exc:
            raise ProviderParseError(SOURCE, "helper output is not JSON") from exc
        if not isinstance(data, dict):
            raise ProviderParseError(SOURCE, "helper output is not a JSON object")
        return _parse_report(device_name, data)

    def _translate_failure(self, exc: ToolFailed) -> Exception:
        if exc.returncode in (_PKEXEC_DISMISSED, _PKEXEC_NOT_AUTHORIZED):
            return PrivilegedActionDenied(ACTION_SMART_REPORT)
        code = _helper_error_code(exc.stderr_snippet)
        if code == "tool-missing":
            return ProviderUnavailable(SOURCE, Availability.TOOL_MISSING, tool="smartmontools")
        if code == "tool-timeout":
            return ProviderTimeout(SOURCE, "smartctl timed out inside the helper")
        if code is None and "lapcare-helper" in exc.stderr_snippet:
            return ProviderParseError(SOURCE, "helper failed")
        if code is None:
            # pkexec itself failed some other way (e.g. helper not installed:
            # "Error executing command as another user" paths vary by version).
            return ProviderUnavailable(
                SOURCE, Availability.TOOL_MISSING, tool="lapcare-helper (installed package)"
            )
        return ProviderParseError(SOURCE, f"helper: {code}")


def _helper_error_code(stderr_snippet: str) -> str | None:
    """Extract <code> from the §13 error line ``lapcare-helper: <code>[: …]``."""
    for line in stderr_snippet.splitlines():
        if line.startswith("lapcare-helper: "):
            return line.split(": ", 2)[1].strip() or None
    return None


# -- smartctl --json parsing (the ONE place this format is known) -------------


def _get_int(data: dict[str, Any], *path: str) -> int | None:
    node: Any = data
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node if isinstance(node, int) and not isinstance(node, bool) else None


def _get_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) and value else None


def _ata_raw_value(data: dict[str, Any], attr_id: int) -> int | None:
    table = data.get("ata_smart_attributes", {})
    rows = table.get("table") if isinstance(table, dict) else None
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and row.get("id") == attr_id:
            raw = row.get("raw")
            if isinstance(raw, dict):
                value = raw.get("value")
                if isinstance(value, int) and not isinstance(value, bool):
                    return value
    return None


def _messages(data: dict[str, Any]) -> tuple[str, ...]:
    smartctl = data.get("smartctl")
    entries = smartctl.get("messages") if isinstance(smartctl, dict) else None
    if not isinstance(entries, list):
        return ()
    out = []
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("string"), str):
            out.append(entry["string"])
    return tuple(out)


def _parse_report(device_name: str, data: dict[str, Any]) -> SmartReport:
    status = data.get("smart_status")
    passed = status.get("passed") if isinstance(status, dict) else None
    return SmartReport(
        device_name=device_name,
        passed=passed if isinstance(passed, bool) else None,
        temperature_c=_get_int(data, "temperature", "current"),
        power_on_hours=_get_int(data, "power_on_time", "hours"),
        power_cycles=_get_int(data, "power_cycle_count"),
        percentage_used=_get_int(data, "nvme_smart_health_information_log", "percentage_used"),
        available_spare_pct=_get_int(data, "nvme_smart_health_information_log", "available_spare"),
        media_errors=_get_int(data, "nvme_smart_health_information_log", "media_errors"),
        critical_warning=_get_int(data, "nvme_smart_health_information_log", "critical_warning"),
        unsafe_shutdowns=_get_int(data, "nvme_smart_health_information_log", "unsafe_shutdowns"),
        reallocated_sectors=_ata_raw_value(data, 5),
        pending_sectors=_ata_raw_value(data, 197),
        model=_get_str(data, "model_name"),
        firmware_version=_get_str(data, "firmware_version"),
        serial_number=_get_str(data, "serial_number"),
        messages=_messages(data),
    )
