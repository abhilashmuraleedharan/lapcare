# SPDX-License-Identifier: GPL-3.0-or-later
"""Logging spine: stderr, captured by the systemd user journal.

No log files, no rotation — the journal already does both (`journalctl --user`).
Level rules (STYLEGUIDE.md): DEBUG raw provider data summaries · INFO lifecycle
and user actions · WARNING degraded states · ERROR failures shown to the user.
Identifiers (serials, UUIDs, MACs) must never appear above DEBUG; that is a
review rule enforced in PRs, not code.
"""

from __future__ import annotations

import logging
import os
import sys


def configure(verbose: bool = False) -> None:
    """Configure process-wide logging once, at startup (called by app.main).

    DEBUG when ``verbose`` or the environment sets ``LAPCARE_DEBUG=1``.
    """
    debug = verbose or os.environ.get("LAPCARE_DEBUG") == "1"
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug else logging.INFO)
