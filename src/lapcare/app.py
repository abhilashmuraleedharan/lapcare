# SPDX-License-Identifier: GPL-3.0-or-later
"""Application entry point and composition root.

Milestone M0 state: parses arguments, configures logging, logs startup, and
exits. The Adw.Application shell arrives in M0 Commit 10; provider wiring
begins in M1. This module is the only place concrete implementations are
constructed and wired together (see ARCHITECTURE.md).
"""
from __future__ import annotations

import argparse
import logging
import os

from lapcare import __version__

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lapcare",
        description="Battery health, firmware updates and diagnostics for ThinkPads.",
    )
    parser.add_argument("--version", action="version", version=f"lapcare {__version__}")
    parser.add_argument("--verbose", action="store_true", help="enable debug logging")
    args = parser.parse_args(argv)

    debug = args.verbose or os.environ.get("LAPCARE_DEBUG") == "1"
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    log.info("starting version=%s", __version__)
    return 0
