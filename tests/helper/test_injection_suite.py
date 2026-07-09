# SPDX-License-Identifier: GPL-3.0-or-later
"""The ADR-0006 §18 negative/injection suite for lapcare-helper.

Two layers, matching how each rule can fail:
- subprocess tests run the helper exactly as pkexec would (real argv, real
  /sys/block) and assert the argument-validation rules — these fire before
  privilege is relevant, so the suite is meaningful unprivileged (§18);
- import tests load the module and substitute the `os`/`subprocess` module
  objects in its namespace to drive the execution-hygiene rules (timeout,
  bitmask policy, output cap, JSON gate) without root or real devices.

Changing the helper without extending this suite violates its definition of
done (docs/security-design.md).
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

HELPER = Path(__file__).resolve().parents[2] / "helper" / "lapcare_helper.py"
DEVICE = "nvme0n1"
GOOD_JSON = json.dumps({"smart_status": {"passed": True}}).encode()


def run_helper(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(HELPER), *args],
        capture_output=True,
        timeout=30,
        check=False,
    )


def assert_rejected(proc: subprocess.CompletedProcess[bytes], code: str) -> None:
    assert proc.returncode != 0
    assert proc.stdout == b"", "stdout must be empty on error (ADR-0006 §13)"
    assert proc.stderr.startswith(f"lapcare-helper: {code}".encode())


# --- argument validation, run exactly as pkexec would run us ---------------


def test_no_arguments_is_usage() -> None:
    assert_rejected(run_helper(), "usage")


def test_missing_device_argument_is_usage() -> None:
    assert_rejected(run_helper("smart-report"), "usage")


def test_extra_arguments_are_usage() -> None:
    assert_rejected(run_helper("smart-report", "sda", "sdb"), "usage")


@pytest.mark.parametrize(
    "verb",
    [
        "nvme-report",  # ADR-defined but not shipped: must NOT dispatch
        "dmi-full",
        "smart_report",
        "SMART-REPORT",
        "smart-report ",
        "--help",
        "--",
        "",
    ],
)
def test_unknown_verbs_are_rejected(verb: str) -> None:
    assert_rejected(run_helper(verb, "sda"), "unknown-verb")


@pytest.mark.parametrize(
    "device",
    [
        "/dev/sda",  # paths never accepted, even to real devices
        "../sda",
        "sda/../nvme0n1",
        "/usr/bin/sh",
        "dev/sda",
        ".",
        "..",
        "",
        " sda",
        "sda ",
        "sda\n",
        "sd a",
        "$(reboot)",
        "`id`",
        "sda;id",
        "zz99nope",  # well-formed name, not a present device
    ],
)
def test_hostile_device_arguments_are_rejected(device: str) -> None:
    proc = run_helper("smart-report", device)
    assert_rejected(proc, "unknown-device")
    if device.strip("\n "):
        # §13: the rejected argument is never echoed back.
        assert device.encode() not in proc.stderr


# --- execution hygiene, driven by substituting os/subprocess ----------------


def load_helper() -> Any:
    spec = importlib.util.spec_from_file_location("lapcare_helper", HELPER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_os(*, node_exists: bool = True, is_block: bool = True, tool: bool = True) -> Any:
    mode = (stat.S_IFBLK if is_block else stat.S_IFREG) | 0o660

    def _stat(path: str) -> Any:
        if not node_exists:
            raise FileNotFoundError(path)
        return SimpleNamespace(st_mode=mode)

    return SimpleNamespace(
        listdir=lambda _path: [DEVICE],
        stat=_stat,
        access=lambda _path, _mode: tool,
        X_OK=os.X_OK,
    )


def fake_subprocess(
    *, returncode: int = 0, stdout: bytes = GOOD_JSON, timeout: bool = False
) -> Any:
    def _run(argv: list[str], **kwargs: Any) -> Any:
        assert argv[0] == "/usr/sbin/smartctl", "absolute tool path only (ADR-0006 §8)"
        assert kwargs["env"] == {
            "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
            "LC_ALL": "C.UTF-8",
        }, "scrubbed child environment (ADR-0006 §9)"
        assert kwargs["timeout"] == 25 and kwargs["cwd"] == "/"
        if timeout:
            raise subprocess.TimeoutExpired(argv, 25)
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=b"")

    return types.SimpleNamespace(
        run=_run,
        TimeoutExpired=subprocess.TimeoutExpired,
        DEVNULL=subprocess.DEVNULL,
    )


def expect_ok(helper: Any) -> None:
    assert helper.main(["lapcare-helper", "smart-report", DEVICE]) == 0


def expect_fail(helper: Any, capsys: pytest.CaptureFixture[str], code: str) -> None:
    with pytest.raises(SystemExit) as exc:
        helper.main(["lapcare-helper", "smart-report", DEVICE])
    assert exc.value.code == 1
    assert capsys.readouterr().err.startswith(f"lapcare-helper: {code}")


def test_matched_device_passes_json_through(
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    helper = load_helper()
    helper.os = fake_os()
    helper.subprocess = fake_subprocess()
    expect_ok(helper)
    assert capfdbinary.readouterr().out == GOOD_JSON


@pytest.mark.parametrize("rc", [8, 0xF8])
def test_failing_disk_bits_are_data_not_error(
    rc: int, capfdbinary: pytest.CaptureFixture[bytes]
) -> None:
    # bits 3-7 (e.g. 8 = "disk failing", 0xF8 = all findings) still emit JSON.
    helper = load_helper()
    helper.os = fake_os()
    helper.subprocess = fake_subprocess(returncode=rc)
    expect_ok(helper)
    assert capfdbinary.readouterr().out == GOOD_JSON


@pytest.mark.parametrize("rc", [1, 2, 4, 7, -9])
def test_fatal_smartctl_exits_are_tool_failed(rc: int, capsys: pytest.CaptureFixture[str]) -> None:
    helper = load_helper()
    helper.os = fake_os()
    helper.subprocess = fake_subprocess(returncode=rc)
    expect_fail(helper, capsys, "tool-failed")


def test_matched_name_without_device_node(capsys: pytest.CaptureFixture[str]) -> None:
    helper = load_helper()
    helper.os = fake_os(node_exists=False)
    expect_fail(helper, capsys, "unknown-device")


def test_matched_name_that_is_not_a_block_device(capsys: pytest.CaptureFixture[str]) -> None:
    helper = load_helper()
    helper.os = fake_os(is_block=False)
    expect_fail(helper, capsys, "unknown-device")


def test_tool_missing(capsys: pytest.CaptureFixture[str]) -> None:
    helper = load_helper()
    helper.os = fake_os(tool=False)
    expect_fail(helper, capsys, "tool-missing")


def test_tool_timeout_is_reported(capsys: pytest.CaptureFixture[str]) -> None:
    helper = load_helper()
    helper.os = fake_os()
    helper.subprocess = fake_subprocess(timeout=True)
    expect_fail(helper, capsys, "tool-timeout")


def test_non_json_output_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    helper = load_helper()
    helper.os = fake_os()
    helper.subprocess = fake_subprocess(stdout=b"<html>not json</html>")
    expect_fail(helper, capsys, "output-invalid")


def test_oversized_output_is_an_error_not_a_truncation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    helper = load_helper()
    helper.os = fake_os()
    huge = b'{"pad": "' + b"x" * helper.MAX_OUTPUT_BYTES + b'"}'
    helper.subprocess = fake_subprocess(stdout=huge)
    expect_fail(helper, capsys, "output-invalid")
