# SPDX-License-Identifier: GPL-3.0-or-later
"""Sanity tests: the package skeleton imports and the entry point works."""

import re

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


def test_main_exits_zero() -> None:
    assert app.main([]) == 0


def test_main_verbose_exits_zero() -> None:
    assert app.main(["--verbose"]) == 0
