# SPDX-License-Identifier: GPL-3.0-or-later
"""storage_smart provider: inventory against the E16 sysfs fixture, SMART
parsing against real (E16 NVMe) and synthetic (failing SATA) smartctl JSON
through a fake runner, and every §15 error translation."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from lapcare.core.errors import (
    PrivilegedActionDenied,
    ProviderParseError,
    ProviderTimeout,
    ProviderUnavailable,
)
from lapcare.core.models import Availability
from lapcare.platform.subprocess import ToolFailed, ToolNotFound, ToolTimeout
from lapcare.providers.storage_smart import (
    ACTION_SMART_REPORT,
    HELPER_PATH,
    StorageSmartPkexec,
)

from .conftest import fixture_root

E16 = fixture_root("storage_smart", "thinkpad-e16-gen2")
SATA = fixture_root("storage_smart", "synthetic-failing-sata")


class FakeRunner:
    """Returns canned stdout or raises; records the exact invocation."""

    def __init__(self, stdout: str = "", raises: Exception | None = None) -> None:
        self.stdout = stdout
        self.raises = raises
        self.calls: list[tuple[str, list[str], float]] = []

    async def __call__(self, tool: str, args: Sequence[str], *, timeout: float = 10.0) -> str:
        self.calls.append((tool, list(args), timeout))
        if self.raises is not None:
            raise self.raises
        return self.stdout


def e16_json() -> str:
    return (E16 / "smartctl-nvme0n1.json").read_text()


# -- unprivileged inventory ---------------------------------------------------


def test_availability_ok_on_fixture() -> None:
    assert StorageSmartPkexec(root=E16).availability() is Availability.OK


def test_availability_without_sys_block(tmp_path: Path) -> None:
    assert StorageSmartPkexec(root=tmp_path).availability() is Availability.UNSUPPORTED_HARDWARE


async def test_inventory_maps_fields_and_skips_virtual_devices() -> None:
    (device,) = await StorageSmartPkexec(root=E16).list_devices()  # loop0 skipped
    assert device.name == "nvme0n1"
    assert device.model == "SKHynix_HFS512GEM4X169N"
    assert device.size_bytes == 1000215216 * 512
    assert device.removable is False
    assert device.rotational is False


async def test_inventory_empty_sys_block_is_empty_list(tmp_path: Path) -> None:
    (tmp_path / "sys/block").mkdir(parents=True)
    assert await StorageSmartPkexec(root=tmp_path).list_devices() == []


# -- SMART parsing ------------------------------------------------------------


async def test_smart_report_e16_nvme() -> None:
    runner = FakeRunner(stdout=e16_json())
    report = await StorageSmartPkexec(root=E16, runner=runner).read_smart("nvme0n1")

    assert runner.calls == [("pkexec", [HELPER_PATH, "smart-report", "nvme0n1"], 120.0)]
    assert report.passed is True
    assert report.temperature_c == 43
    assert report.percentage_used == 2
    assert report.available_spare_pct == 100
    assert report.media_errors == 0
    assert report.critical_warning == 0
    assert report.unsafe_shutdowns == 107
    assert report.power_on_hours == 278
    assert report.power_cycles == 608
    assert report.model == "SKHynix_HFS512GEM4X169N"
    assert report.serial_number == "REDACTED0000000000"
    assert report.reallocated_sectors is None  # NVMe has no ATA table
    # The E16 quirk: bit-2 exit's message arrives as a data-quality note.
    assert any("Self-test Log" in m for m in report.messages)


async def test_smart_report_failing_sata() -> None:
    runner = FakeRunner(stdout=(SATA / "smartctl-sda.json").read_text())
    report = await StorageSmartPkexec(root=SATA, runner=runner).read_smart("sda")
    assert report.passed is False
    assert report.reallocated_sectors == 1264
    assert report.pending_sectors == 88
    assert report.temperature_c == 51
    assert report.percentage_used is None  # no NVMe section on ATA
    assert report.messages == ()


async def test_smart_report_minimal_json_is_all_none() -> None:
    runner = FakeRunner(stdout="{}")
    report = await StorageSmartPkexec(runner=runner).read_smart("sda")
    assert report.passed is None
    assert report.temperature_c is None
    assert report.serial_number is None


# -- error translation (ADR-0006 §15) -----------------------------------------


async def test_pkexec_missing_is_tool_missing() -> None:
    runner = FakeRunner(raises=ToolNotFound("pkexec"))
    with pytest.raises(ProviderUnavailable) as exc:
        await StorageSmartPkexec(runner=runner).read_smart("sda")
    assert exc.value.tool == "pkexec"


@pytest.mark.parametrize("returncode", [126, 127])
async def test_pkexec_denied_is_privileged_action_denied(returncode: int) -> None:
    runner = FakeRunner(raises=ToolFailed("pkexec", returncode, ""))
    with pytest.raises(PrivilegedActionDenied) as exc:
        await StorageSmartPkexec(runner=runner).read_smart("sda")
    assert exc.value.action == ACTION_SMART_REPORT


async def test_helper_tool_missing_names_smartmontools() -> None:
    runner = FakeRunner(
        raises=ToolFailed("pkexec", 1, "lapcare-helper: tool-missing: /usr/sbin/smartctl")
    )
    with pytest.raises(ProviderUnavailable) as exc:
        await StorageSmartPkexec(runner=runner).read_smart("sda")
    assert exc.value.reason is Availability.TOOL_MISSING
    assert exc.value.tool == "smartmontools"


async def test_helper_timeout_is_provider_timeout() -> None:
    runner = FakeRunner(
        raises=ToolFailed("pkexec", 1, "lapcare-helper: tool-timeout: smartctl exceeded 25s")
    )
    with pytest.raises(ProviderTimeout):
        await StorageSmartPkexec(runner=runner).read_smart("sda")


async def test_helper_other_error_is_parse_error() -> None:
    runner = FakeRunner(raises=ToolFailed("pkexec", 1, "lapcare-helper: unknown-device"))
    with pytest.raises(ProviderParseError) as exc:
        await StorageSmartPkexec(runner=runner).read_smart("sda")
    assert "unknown-device" in exc.value.detail


async def test_helper_not_installed_is_tool_missing() -> None:
    # pkexec's own error (no §13 line on stderr): dev builds run uninstalled.
    runner = FakeRunner(raises=ToolFailed("pkexec", 1, "Error executing command as another user"))
    with pytest.raises(ProviderUnavailable) as exc:
        await StorageSmartPkexec(runner=runner).read_smart("sda")
    assert exc.value.reason is Availability.TOOL_MISSING


async def test_client_pkexec_timeout_is_provider_timeout() -> None:
    runner = FakeRunner(raises=ToolTimeout("pkexec", 120.0))
    with pytest.raises(ProviderTimeout):
        await StorageSmartPkexec(runner=runner).read_smart("sda")


async def test_non_json_helper_output_is_parse_error() -> None:
    runner = FakeRunner(stdout="not json at all")
    with pytest.raises(ProviderParseError):
        await StorageSmartPkexec(runner=runner).read_smart("sda")


async def test_non_object_json_is_parse_error() -> None:
    runner = FakeRunner(stdout=json.dumps([1, 2, 3]))
    with pytest.raises(ProviderParseError):
        await StorageSmartPkexec(runner=runner).read_smart("sda")


async def test_hostile_json_types_map_to_none_never_crash() -> None:
    # The helper guarantees valid JSON, not a valid SCHEMA (ADR-0006 §12/§16):
    # every field read must survive adversarial/broken types.
    hostile = {
        "smart_status": "banana",
        "temperature": [1, 2],
        "power_on_time": {"hours": "many"},
        "power_cycle_count": True,  # bool is not an int here
        "nvme_smart_health_information_log": 7,
        "ata_smart_attributes": {"table": {"id": 5}},
        "model_name": 3,
        "firmware_version": "",
        "serial_number": None,
        "smartctl": {"messages": [{"string": 42}, "nope", {"no_string": 1}]},
    }
    runner = FakeRunner(stdout=json.dumps(hostile))
    report = await StorageSmartPkexec(runner=runner).read_smart("sda")
    assert report.passed is None
    assert report.temperature_c is None
    assert report.power_on_hours is None
    assert report.power_cycles is None
    assert report.percentage_used is None
    assert report.reallocated_sectors is None
    assert report.model is None
    assert report.firmware_version is None
    assert report.serial_number is None
    assert report.messages == ()
