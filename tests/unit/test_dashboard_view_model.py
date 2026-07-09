# SPDX-License-Identifier: GPL-3.0-or-later
"""Dashboard view-model: display-free, driven by real providers over fixtures.

Uses an ImmediateScheduler (runs the coroutine synchronously) so no GLib main
loop or display is needed — the pattern for all page view-model tests.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from lapcare.core.errors import ProviderUnavailable
from lapcare.core.models import Availability
from lapcare.providers.dmi import DmiSysfs
from lapcare.providers.os_info import OsInfoProc
from lapcare.providers.thinkpad_acpi import ThinkpadAcpiSysfs
from lapcare.ui.pages.dashboard.view_model import DashboardViewModel, format_uptime

from ..providers.conftest import fixture_root

T = TypeVar("T")


class ImmediateScheduler:
    """Test double: executes the coroutine now, callbacks synchronously."""

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def submit(
        self,
        coro: Coroutine[Any, Any, T],
        on_success: Callable[[T], None],
        on_error: Callable[[BaseException], None],
    ) -> None:
        try:
            on_success(asyncio.run(coro))
        except Exception as exc:
            on_error(exc)


def _e16_view_model() -> DashboardViewModel:
    dmi = DmiSysfs(root=fixture_root("dmi", "thinkpad-e16-gen2"))
    return DashboardViewModel(
        ImmediateScheduler(),
        identity=dmi,
        os_info=OsInfoProc(root=fixture_root("os_info", "synthetic-full")),
        thinkpad=ThinkpadAcpiSysfs(
            root=fixture_root("thinkpad_acpi", "thinkpad-e16-gen2"), identity=dmi
        ),
    )


def test_ready_with_e16_fixtures() -> None:
    vm = _e16_view_model()
    vm.load()
    assert vm.props.state == "ready"
    assert vm.props.model == "ThinkPad E16 Gen 2"
    assert vm.props.machine_type == "21MBCTO1WW"
    assert vm.props.vendor == "LENOVO"
    # The space inside the parens is genuinely what the E16's firmware reports.
    assert vm.props.bios == "R2JET48W(1.25 ) (04/27/2026)"
    assert vm.props.distro == "Ubuntu 24.04.2 LTS"
    assert vm.props.kernel == "6.8.0-124-generic"
    assert vm.props.is_thinkpad


def test_non_thinkpad_sets_banner_flag() -> None:
    dmi = DmiSysfs(root=fixture_root("dmi", "qemu-vm"))
    vm = DashboardViewModel(
        ImmediateScheduler(),
        identity=dmi,
        os_info=OsInfoProc(root=fixture_root("os_info", "synthetic-full")),
        thinkpad=ThinkpadAcpiSysfs(root=fixture_root("dmi", "qemu-vm"), identity=dmi),
    )
    vm.load()
    assert vm.props.state == "ready"
    assert not vm.props.is_thinkpad
    assert vm.props.vendor == "QEMU"


def test_provider_unavailable_maps_to_unavailable_state() -> None:
    class Unavailable:
        def availability(self) -> Availability:
            return Availability.TOOL_MISSING

        async def read_identity(self):
            raise ProviderUnavailable("dmi", Availability.TOOL_MISSING, tool="example")

    vm = DashboardViewModel(
        ImmediateScheduler(),
        identity=Unavailable(),
        os_info=OsInfoProc(root=fixture_root("os_info", "synthetic-full")),
        thinkpad=ThinkpadAcpiSysfs(root=fixture_root("dmi", "qemu-vm")),
    )
    vm.load()
    assert vm.props.state == "unavailable"
    assert "example" in vm.props.unavailable_remedy


def test_unexpected_error_maps_to_error_state() -> None:
    class Broken:
        def availability(self) -> Availability:
            return Availability.OK

        async def read_identity(self):
            raise RuntimeError("boom")

    vm = DashboardViewModel(
        ImmediateScheduler(),
        identity=Broken(),
        os_info=OsInfoProc(root=fixture_root("os_info", "synthetic-full")),
        thinkpad=ThinkpadAcpiSysfs(root=fixture_root("dmi", "qemu-vm")),
    )
    vm.load()
    assert vm.props.state == "error"
    assert "boom" in vm.props.error_detail


def test_format_uptime() -> None:
    assert format_uptime(None) == "—"
    assert format_uptime(59) == "0m"
    assert format_uptime(3 * 3600 + 5 * 60) == "3h 5m"
    assert format_uptime(2 * 86400 + 3600) == "2d 1h 0m"


def test_health_score_card_from_unprivileged_signals() -> None:
    from .test_diagnostics_view_model import FakeDisk, FakeFirmware, FakeThermal

    vm = _e16_view_model()  # no health providers: card stays hidden
    vm.load()
    assert vm.props.health_score == ""

    dmi = DmiSysfs(root=fixture_root("dmi", "thinkpad-e16-gen2"))
    vm = DashboardViewModel(
        ImmediateScheduler(),
        identity=dmi,
        os_info=OsInfoProc(root=fixture_root("os_info", "synthetic-full")),
        thinkpad=ThinkpadAcpiSysfs(
            root=fixture_root("thinkpad_acpi", "thinkpad-e16-gen2"), identity=dmi
        ),
        firmware=FakeFirmware([]),
        thermal=FakeThermal(),
        disk=FakeDisk(),
    )
    vm.load()
    assert vm.props.state == "ready"
    assert vm.props.health_score == "100 / 100"
    # Storage SMART is never read from the Dashboard (zero prompts): it
    # counts as unmeasured coverage. Battery provider absent here too.
    assert "3 of 5" in vm.props.health_coverage
    assert "Experimental" in vm.props.health_coverage
