# SPDX-License-Identifier: GPL-3.0-or-later
"""disk_usage provider against the synthetic mounts table + fake statvfs."""

from __future__ import annotations

import os
from pathlib import Path

from lapcare.core.models import Availability
from lapcare.providers.disk_usage import DiskUsageStatvfs

from .conftest import fixture_root

MOUNTS = fixture_root("disk_usage", "synthetic-mounts")


def fake_statvfs(sizes: dict[str, tuple[int, int]]):  # type: ignore[no-untyped-def]
    """sizes: mountpoint -> (total_blocks, avail_blocks) at 4096 frsize."""

    def _statvfs(path: str) -> os.statvfs_result:
        if path not in sizes:
            raise OSError(f"no such mount: {path}")
        total, avail = sizes[path]
        return os.statvfs_result((4096, 4096, total, avail, avail, 0, 0, 0, 0, 255))

    return _statvfs


def test_availability() -> None:
    assert DiskUsageStatvfs(root=MOUNTS).availability() is Availability.OK


def test_availability_without_proc(tmp_path: Path) -> None:
    assert DiskUsageStatvfs(root=tmp_path).availability() is Availability.UNSUPPORTED_HARDWARE


async def test_real_mounts_only_deduped_by_source() -> None:
    statvfs = fake_statvfs(
        {
            "/": (1000, 500),
            "/boot/efi": (100, 90),
            "/mnt/usb drive": (200, 10),
        }
    )
    usages = await DiskUsageStatvfs(root=MOUNTS, statvfs=statvfs).list_usage()
    mounts = [u.mountpoint for u in usages]
    # /var/lib/docker (same source as /) and all pseudo-fs are excluded;
    # the \040 escape decodes to a space.
    assert mounts == ["/", "/boot/efi", "/mnt/usb drive"]
    root = usages[0]
    assert root.total_bytes == 1000 * 4096
    assert root.free_bytes == 500 * 4096


async def test_failing_statvfs_skips_that_mount() -> None:
    statvfs = fake_statvfs({"/": (1000, 500)})  # others raise
    usages = await DiskUsageStatvfs(root=MOUNTS, statvfs=statvfs).list_usage()
    assert [u.mountpoint for u in usages] == ["/"]


async def test_missing_proc_mounts_is_empty(tmp_path: Path) -> None:
    assert await DiskUsageStatvfs(root=tmp_path).list_usage() == []
