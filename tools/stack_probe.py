#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Report the versions and capabilities of the lapcare stack on this system.

Used by the M0 stack-validation spike (ADR-0007) and kept as a diagnostic:
run it inside any environment (`./run`-style native, dev container, CI) to
see exactly what the platform offers. Exit code 0 if the environment can run
lapcare at all; 1 if a hard requirement is missing.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys


def probe() -> int:
    ok = True
    print(f"python           {platform.python_version()}")

    try:
        import gi

        print(f"pygobject        {gi.__version__}")
    except ImportError:
        print("pygobject        MISSING (hard requirement)")
        return 1

    try:
        from gi.repository import GLib

        print(f"glib             {GLib.MAJOR_VERSION}.{GLib.MINOR_VERSION}.{GLib.MICRO_VERSION}")
    except ImportError as e:
        print(f"glib             MISSING ({e})")
        ok = False

    try:
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk

        print(
            f"gtk4             "
            f"{Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}"
        )
    except (ValueError, ImportError) as e:
        print(f"gtk4             MISSING ({e})")
        ok = False

    try:
        gi.require_version("Adw", "1")
        from gi.repository import Adw

        print(f"libadwaita       {Adw.get_major_version()}.{Adw.get_minor_version()}.{Adw.get_micro_version()}")
        if (Adw.get_major_version(), Adw.get_minor_version()) < (1, 4):
            print("                 ^ below 1.4: NavigationSplitView unavailable")
            ok = False
    except (ValueError, ImportError):
        print("libadwaita       MISSING (hard requirement)")
        ok = False

    # The ADR-0007 question: native asyncio integration or executor fallback?
    try:
        import gi.events  # noqa: F401

        print("gi.events        AVAILABLE -> native asyncio integration")
    except ImportError:
        print("gi.events        absent -> platform executor fallback (ADR-0007)")

    try:
        import dbusmock

        print(f"dbusmock         {dbusmock.__version__}")
    except ImportError:
        print("dbusmock         missing (tests will not run)")

    for tool in ("meson", "blueprint-compiler", "desktop-file-validate", "appstreamcli"):
        path = shutil.which(tool)
        if path is None:
            print(f"{tool:16} MISSING")
            continue
        try:
            out = subprocess.run(
                [path, "--version"], capture_output=True, text=True, timeout=10
            ).stdout.strip().splitlines()
            print(f"{tool:16} {out[0] if out else '?'}")
        except (subprocess.SubprocessError, OSError):
            print(f"{tool:16} present (version unknown)")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(probe())
