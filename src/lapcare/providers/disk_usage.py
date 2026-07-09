# SPDX-License-Identifier: GPL-3.0-or-later
"""disk_usage provider: filesystem usage for real mounts via statvfs.

Implements core.ports.DiskUsageProvider. Concrete class DiskUsageStatvfs.

Reads ``/proc/mounts`` (rooted for fixtures) and keeps mounts whose source
starts with ``/dev/`` — the one-line rule that excludes proc/sys/tmpfs/
cgroup/overlay pseudo-filesystems without a fstype blocklist to maintain.
One statvfs entry per source device (a btrfs with many subvolume mounts or
bind mounts counts once, at its first-listed mountpoint). Sizes use
``f_frsize``; free space is ``f_bavail`` (what an unprivileged user can
actually use), matching what file managers report.

A mountpoint whose statvfs fails (stale mount, permission) is skipped with
a DEBUG log. Octal escapes in mountpoints (``\\040`` for space) are decoded
as /proc/mounts defines them.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path

from lapcare.core.models import Availability, DiskUsage
from lapcare.platform.files import read_str

log = logging.getLogger(__name__)

SOURCE = "disk_usage"


def _decode_mount_field(field: str) -> str:
    """/proc/mounts escapes space/tab/newline/backslash as octal (\\040...)."""
    return field.encode().decode("unicode_escape")


class DiskUsageStatvfs:
    def __init__(
        self,
        root: Path = Path("/"),
        statvfs: Callable[[str], os.statvfs_result] = os.statvfs,
    ) -> None:
        self._root = root
        self._statvfs = statvfs

    def availability(self) -> Availability:
        if (self._root / "proc/mounts").exists():
            return Availability.OK
        return Availability.UNSUPPORTED_HARDWARE

    async def list_usage(self) -> list[DiskUsage]:
        text = read_str(self._root / "proc/mounts", max_bytes=1024 * 1024)
        if text is None:
            return []
        usages: list[DiskUsage] = []
        seen_sources: set[str] = set()
        for line in text.splitlines():
            fields = line.split()
            if len(fields) < 2 or not fields[0].startswith("/dev/"):
                continue
            source, mountpoint = fields[0], _decode_mount_field(fields[1])
            if source in seen_sources:
                continue  # subvolume/bind mounts of the same device count once
            seen_sources.add(source)
            try:
                stat = self._statvfs(mountpoint)
            except OSError as exc:
                log.debug("statvfs %s: %s", mountpoint, exc)
                continue
            usages.append(
                DiskUsage(
                    mountpoint=mountpoint,
                    total_bytes=stat.f_frsize * stat.f_blocks,
                    free_bytes=stat.f_frsize * stat.f_bavail,
                )
            )
        return usages
