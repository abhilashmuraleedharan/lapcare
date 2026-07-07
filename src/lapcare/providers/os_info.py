# SPDX-License-Identifier: GPL-3.0-or-later
"""os_info provider: OS release, kernel, uptime, CPU/memory summary.

Implements core.ports.OsInfoProvider. Concrete class OsInfoProc (convention:
concrete providers are named <port-topic><transport>).

Data sources (all world-readable; ``root`` injectable for fixtures):
- ``/etc/os-release``            PRETTY_NAME, VERSION_ID
- ``/proc/sys/kernel/osrelease`` kernel release string
- ``/proc/sys/kernel/hostname``  hostname
- ``/proc/uptime``               "``<uptime_s> <idle_s>``", floats
- ``/proc/cpuinfo``              "model name" (first), count of "processor" entries
- ``/proc/meminfo``              "MemTotal:  16256564 kB"

Stability notes / quirks:
- os-release fields are optional by spec; PRETTY_NAME can be absent.
- ARM (e.g. ThinkPad X13s) cpuinfo has no "model name" line → cpu_model None;
  needs a fixture when ARM support arrives.
- All fields degrade to None individually; availability() is about the
  *filesystem*, not any single file.
"""

from __future__ import annotations

import logging
from pathlib import Path

from lapcare.core.models import Availability, CpuMemSummary, OsInfo
from lapcare.platform.files import read_str

log = logging.getLogger(__name__)

SOURCE = "os_info"


def _parse_os_release(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"')
    return values


class OsInfoProc:
    def __init__(self, root: Path = Path("/")) -> None:
        self._root = root

    def availability(self) -> Availability:
        if (self._root / "proc").is_dir() or (self._root / "etc/os-release").exists():
            return Availability.OK
        return Availability.UNSUPPORTED_HARDWARE

    async def read_os(self) -> OsInfo:
        release_text = read_str(self._root / "etc/os-release", max_bytes=16384)
        release = _parse_os_release(release_text) if release_text else {}

        uptime_seconds: float | None = None
        uptime_text = read_str(self._root / "proc/uptime", max_bytes=128)
        if uptime_text:
            try:
                uptime_seconds = float(uptime_text.split()[0])
            except (ValueError, IndexError):
                log.debug("unparseable /proc/uptime: %.64r", uptime_text)

        return OsInfo(
            distro_name=release.get("PRETTY_NAME"),
            distro_version=release.get("VERSION_ID"),
            kernel=read_str(self._root / "proc/sys/kernel/osrelease", max_bytes=256),
            hostname=read_str(self._root / "proc/sys/kernel/hostname", max_bytes=256),
            uptime_seconds=uptime_seconds,
        )

    async def read_cpu_mem(self) -> CpuMemSummary:
        cpu_model: str | None = None
        cpu_count: int | None = None
        cpuinfo = read_str(self._root / "proc/cpuinfo", max_bytes=1024 * 1024)
        if cpuinfo:
            count = 0
            for line in cpuinfo.splitlines():
                if line.startswith("processor"):
                    count += 1
                elif cpu_model is None and line.startswith("model name"):
                    cpu_model = line.partition(":")[2].strip() or None
            cpu_count = count or None

        memory_total_kib: int | None = None
        meminfo = read_str(self._root / "proc/meminfo", max_bytes=65536)
        if meminfo:
            for line in meminfo.splitlines():
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    try:
                        memory_total_kib = int(parts[1])
                    except (ValueError, IndexError):
                        log.debug("unparseable MemTotal: %.64r", line)
                    break

        return CpuMemSummary(
            cpu_model=cpu_model, cpu_count=cpu_count, memory_total_kib=memory_total_kib
        )
