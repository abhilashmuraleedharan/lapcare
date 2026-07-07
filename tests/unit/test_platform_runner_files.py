# SPDX-License-Identifier: GPL-3.0-or-later
"""Audited runner + bounded file reads: whitelist, timeout, failure, bounds."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lapcare.platform import subprocess as runner
from lapcare.platform.files import read_int, read_str


@pytest.fixture
def allow_test_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(runner.ALLOWED_TOOLS, "echo", ("/usr/bin/echo", "/bin/echo"))
    monkeypatch.setitem(runner.ALLOWED_TOOLS, "sleep", ("/usr/bin/sleep", "/bin/sleep"))
    monkeypatch.setitem(runner.ALLOWED_TOOLS, "false", ("/usr/bin/false", "/bin/false"))
    monkeypatch.setitem(runner.ALLOWED_TOOLS, "ghost", ("/nonexistent/ghost",))


async def test_run_tool_returns_stdout(allow_test_tools: None) -> None:
    assert await runner.run_tool("echo", ["hello"]) == "hello\n"


async def test_run_tool_not_found(allow_test_tools: None) -> None:
    with pytest.raises(runner.ToolNotFound):
        await runner.run_tool("ghost", [])


async def test_run_tool_timeout(allow_test_tools: None) -> None:
    with pytest.raises(runner.ToolTimeout):
        await runner.run_tool("sleep", ["5"], timeout=0.2)


async def test_run_tool_failure_carries_returncode(allow_test_tools: None) -> None:
    with pytest.raises(runner.ToolFailed) as exc:
        await runner.run_tool("false", [])
    assert exc.value.returncode == 1


async def test_unwhitelisted_tool_is_a_programming_error() -> None:
    with pytest.raises(KeyError):
        await runner.run_tool("rm", ["-rf", "/"])


def test_read_str(tmp_path: Path) -> None:
    p = tmp_path / "value"
    p.write_text("  ThinkPad E16 Gen 2\n")
    assert read_str(p) == "ThinkPad E16 Gen 2"
    assert read_str(tmp_path / "missing") is None


def test_read_str_bounds(tmp_path: Path) -> None:
    p = tmp_path / "big"
    p.write_bytes(b"x" * 1000)
    assert read_str(p, max_bytes=100) is None


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores file modes")
def test_read_str_permission_denied_is_none(tmp_path: Path) -> None:
    p = tmp_path / "secret"
    p.write_text("serial")
    p.chmod(0)
    try:
        assert read_str(p) is None
    finally:
        p.chmod(0o600)


def test_read_int(tmp_path: Path) -> None:
    p = tmp_path / "count"
    p.write_text("42\n")
    assert read_int(p) == 42
    p.write_text("not-a-number")
    assert read_int(p) is None
