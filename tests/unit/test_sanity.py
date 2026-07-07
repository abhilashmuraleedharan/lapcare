# SPDX-License-Identifier: GPL-3.0-or-later
"""Sanity tests: the package skeleton imports and the entry point works."""

import re

import pytest

import lapcare
from lapcare import app


def test_version_is_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", lapcare.__version__)


def test_app_id() -> None:
    assert lapcare.APP_ID == "io.github.abhilashmuraleedharan.lapcare"


def test_all_layers_import() -> None:
    import lapcare.core
    import lapcare.core.ports
    import lapcare.platform
    import lapcare.providers
    import lapcare.ui  # noqa: F401


def test_version_flag_exits_zero() -> None:
    # argparse's version action raises SystemExit(0); main([]) would launch
    # the GTK app, which unit tests never do (that's the xvfb smoke test).
    with pytest.raises(SystemExit) as exc:
        app.main(["--version"])
    assert exc.value.code == 0


def test_log_configure_debug_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import logging

    from lapcare.platform import log as platform_log

    root = logging.getLogger()
    old_handlers, old_level = root.handlers[:], root.level
    try:
        root.handlers.clear()
        monkeypatch.setenv("LAPCARE_DEBUG", "1")
        platform_log.configure()
        assert root.level == logging.DEBUG
    finally:
        root.handlers[:] = old_handlers
        root.setLevel(old_level)
