# SPDX-License-Identifier: GPL-3.0-or-later
"""Application entry point and composition root.

The only module that constructs concrete implementations and wires them
together (see ARCHITECTURE.md). Provider wiring begins in M1.

GTK/libadwaita are imported lazily inside _build_application() so that
--version/--help and unit tests work without a display or GTK stack.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from lapcare import APP_ID, __version__
from lapcare.platform import log as platform_log

log = logging.getLogger(__name__)


def _build_application():  # -> Adw.Application (typed loosely: gi is untyped)
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gio, GLib

    from lapcare.ui.window import MainWindow

    class LapcareApplication(Adw.Application):
        def __init__(self) -> None:
            super().__init__(
                application_id=APP_ID,
                flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
            )

        def do_activate(self) -> None:
            window = self.props.active_window
            if window is None:
                window = MainWindow(application=self)
            window.present()
            log.info("window presented")

            # Dev/CI hook (used by the smoke test): auto-quit after N ms.
            auto_quit_ms = os.environ.get("LAPCARE_AUTO_QUIT_MS")
            if auto_quit_ms is not None:
                GLib.timeout_add(int(auto_quit_ms), self.quit)

    return LapcareApplication()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lapcare",
        description="Battery health, firmware updates and diagnostics for ThinkPads.",
    )
    parser.add_argument("--version", action="version", version=f"lapcare {__version__}")
    parser.add_argument("--verbose", action="store_true", help="enable debug logging")
    args = parser.parse_args(argv)

    platform_log.configure(verbose=args.verbose)
    log.info("starting version=%s", __version__)

    # Scheduler must exist before the GLib main loop starts (ADR-0007); it is
    # handed to view-models when pages arrive (M1).
    from lapcare.platform.scheduler import create_scheduler

    scheduler = create_scheduler()
    scheduler.start()
    try:
        app = _build_application()
        return int(app.run([sys.argv[0]]))
    finally:
        scheduler.stop()
