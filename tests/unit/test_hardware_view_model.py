# SPDX-License-Identifier: GPL-3.0-or-later
"""Hardware view-model over the real E16 fixtures, display-free."""

from __future__ import annotations

from lapcare.providers.dmi import DmiSysfs
from lapcare.providers.os_info import OsInfoProc
from lapcare.providers.pci_usb import PciUsbTools
from lapcare.ui.pages.hardware.view_model import HardwareViewModel, format_memory

from ..providers.conftest import fixture_root
from ..providers.test_pci_usb import file_runner
from .test_dashboard_view_model import ImmediateScheduler


def test_ready_with_e16_fixtures() -> None:
    vm = HardwareViewModel(
        ImmediateScheduler(),
        identity=DmiSysfs(root=fixture_root("dmi", "thinkpad-e16-gen2")),
        os_info=OsInfoProc(root=fixture_root("os_info", "synthetic-full")),
        inventory=PciUsbTools(runner=file_runner("thinkpad-e16-gen2")),
    )
    vm.load()
    assert vm.props.state == "ready"
    assert vm.props.family == "ThinkPad E16 Gen 2"
    assert vm.props.machine_type == "21MBCTO1WW"
    assert vm.props.board == "21MBCTO1WW"
    assert vm.props.bios_version == "R2JET48W(1.25 )"
    assert vm.props.cpu_model == "AMD Ryzen 7 7735HS with Radeon Graphics"
    assert vm.props.cpu_count == "2"
    assert vm.props.memory == "15.2 GiB"
    assert len(vm.pci_devices) == 20
    assert len(vm.usb_devices) == 7


def test_inventory_failure_degrades_per_panel_not_whole_page() -> None:
    # Real case: CI/cloud VMs have no USB subsystem and lsusb fails — the
    # page must stay READY with identity data, noting the degraded panels.
    from lapcare.platform.subprocess import ToolNotFound
    from tests.providers.test_pci_usb import raising_runner

    vm = HardwareViewModel(
        ImmediateScheduler(),
        identity=DmiSysfs(root=fixture_root("dmi", "thinkpad-e16-gen2")),
        os_info=OsInfoProc(root=fixture_root("os_info", "synthetic-full")),
        inventory=PciUsbTools(runner=raising_runner(ToolNotFound("lspci"))),
    )
    vm.load()
    assert vm.props.state == "ready"
    assert vm.props.family == "ThinkPad E16 Gen 2"
    assert vm.pci_devices == []
    assert "pciutils" in vm.pci_note
    assert vm.usb_note  # degraded too (same runner)


def test_format_memory() -> None:
    assert format_memory(None) == "—"
    assert format_memory(16 * 1024 * 1024) == "16.0 GiB"
    assert format_memory(15980414) == "15.2 GiB"
