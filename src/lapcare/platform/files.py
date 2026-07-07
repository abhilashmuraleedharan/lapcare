# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded reads for sysfs/procfs files.

sysfs values are small; anything large is wrong. Absence and unreadability
collapse to None (with a DEBUG log) — providers decide what None means for
each field (e.g. dmi product_serial is None unprivileged, by design).
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_MAX_BYTES = 64 * 1024


def read_str(path: Path, *, max_bytes: int = DEFAULT_MAX_BYTES) -> str | None:
    """Return the stripped text content of ``path``, or None if unreadable."""
    try:
        with path.open("rb") as f:
            data = f.read(max_bytes + 1)
    except OSError as exc:
        log.debug("read %s: %s", path, exc)
        return None
    if len(data) > max_bytes:
        log.debug("read %s: exceeds %d bytes, treating as unreadable", path, max_bytes)
        return None
    return data.decode(errors="replace").strip()


def read_int(path: Path) -> int | None:
    text = read_str(path, max_bytes=64)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        log.debug("read %s: not an integer: %.32r", path, text)
        return None
