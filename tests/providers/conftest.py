# SPDX-License-Identifier: GPL-3.0-or-later
"""Provider-test helpers: fixture roots under tests/fixtures/<source>/<machine>/."""

from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def fixture_root(source: str, machine: str) -> Path:
    root = FIXTURES / source / machine
    assert root.is_dir(), f"missing fixture: {root}"
    return root
