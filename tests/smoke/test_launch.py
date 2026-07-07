# SPDX-License-Identifier: GPL-3.0-or-later
"""End-to-end smoke test: launch the real app, cycle every page state, quit.

Needs a display server (xvfb in CI) and a meson-built gresource bundle, so it
runs only when LAPCARE_SMOKE_TEST=1 — plain ./check skips it. CI invocation:

    meson setup build && meson compile -C build
    xvfb-run -a dbus-run-session env LAPCARE_SMOKE_TEST=1 GTK_A11Y=none \
        python3 -m pytest tests/smoke -v

Any GTK/GLib/Adwaita CRITICAL in the app's output fails the test.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GRESOURCE = REPO / "build" / "src" / "lapcare.gresource"

pytestmark = pytest.mark.skipif(
    os.environ.get("LAPCARE_SMOKE_TEST") != "1",
    reason="smoke: needs xvfb + built gresource; set LAPCARE_SMOKE_TEST=1",
)


def test_app_launches_cycles_all_states_and_quits_cleanly() -> None:
    assert GRESOURCE.exists(), (
        "gresource not built — run: meson setup build && meson compile -C build"
    )

    env = os.environ | {
        "LAPCARE_RESOURCE": str(GRESOURCE),
        "LAPCARE_AUTO_QUIT_MS": "3000",
        "LAPCARE_SMOKE": "1",
        "PYTHONPATH": str(REPO / "src"),
        "GTK_A11Y": "none",
    }
    proc = subprocess.run(
        [sys.executable, "-m", "lapcare", "--verbose"],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = proc.stdout + proc.stderr

    assert proc.returncode == 0, f"app exited {proc.returncode}:\n{output}"
    assert "CRITICAL" not in output, f"GTK criticals in output:\n{output}"
    assert "window presented" in output, output
    assert "smoke: cycled all states" in output, output
