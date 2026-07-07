# SPDX-License-Identifier: GPL-3.0-or-later
"""pci_usb provider against real E16 Gen 2 command captures + error paths."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from lapcare.core.errors import ProviderParseError, ProviderTimeout, ProviderUnavailable
from lapcare.core.models import Availability
from lapcare.platform.subprocess import ToolFailed, ToolNotFound, ToolTimeout
from lapcare.providers.pci_usb import PciUsbTools

from .conftest import fixture_root


def file_runner(machine: str):
    async def run(tool: str, args: Sequence[str], *, timeout: float = 10.0) -> str:
        path = fixture_root("pci_usb", machine) / f"{tool}.txt"
        if not path.exists():
            raise ToolNotFound(tool)
        return path.read_text()

    return run


def raising_runner(exc: Exception):
    async def run(tool: str, args: Sequence[str], *, timeout: float = 10.0) -> str:
        raise exc

    return run


async def test_e16_gen2_pci_capture() -> None:
    provider = PciUsbTools(runner=file_runner("thinkpad-e16-gen2"))
    devices = await provider.list_pci()
    assert len(devices) == 20
    vga = next(d for d in devices if d.slot == "00:02.0")
    assert vga.device_class == "VGA compatible controller"
    assert vga.vendor == "Intel Corporation"


async def test_e16_gen2_usb_capture() -> None:
    provider = PciUsbTools(runner=file_runner("thinkpad-e16-gen2"))
    devices = await provider.list_usb()
    assert len(devices) == 7
    camera = next(d for d in devices if d.vendor_id == "174f")
    assert camera.product_id == "1820"
    assert camera.name == "Syntek Integrated Camera"
    assert camera.bus == "003"


async def test_tool_missing_maps_to_unavailable() -> None:
    provider = PciUsbTools(runner=raising_runner(ToolNotFound("lspci")))
    with pytest.raises(ProviderUnavailable) as exc:
        await provider.list_pci()
    assert exc.value.reason is Availability.TOOL_MISSING
    assert exc.value.tool == "pciutils"


async def test_timeout_maps_to_provider_timeout() -> None:
    provider = PciUsbTools(runner=raising_runner(ToolTimeout("lsusb", 10.0)))
    with pytest.raises(ProviderTimeout):
        await provider.list_usb()


async def test_tool_failure_maps_to_parse_error() -> None:
    provider = PciUsbTools(runner=raising_runner(ToolFailed("lspci", 1, "boom")))
    with pytest.raises(ProviderParseError):
        await provider.list_pci()


async def test_garbage_output_is_parse_error() -> None:
    async def garbage(tool: str, args: Sequence[str], *, timeout: float = 10.0) -> str:
        return "complete nonsense without structure\n"

    with pytest.raises(ProviderParseError):
        await PciUsbTools(runner=garbage).list_usb()


async def test_partial_garbage_is_skipped_not_fatal() -> None:
    real = fixture_root("pci_usb", "thinkpad-e16-gen2") / "lsusb.txt"

    async def mixed(tool: str, args: Sequence[str], *, timeout: float = 10.0) -> str:
        return "junk line\n" + real.read_text()

    devices = await PciUsbTools(runner=mixed).list_usb()
    assert len(devices) == 7
