# SPDX-License-Identifier: GPL-3.0-or-later
"""ThinkPad detection: both signals, each signal alone, and neither."""

from __future__ import annotations

from pathlib import Path

from lapcare.core.models import Availability
from lapcare.providers.dmi import DmiSysfs
from lapcare.providers.thinkpad_acpi import ThinkpadAcpiSysfs

from .conftest import fixture_root


async def test_e16_gen2_both_signals() -> None:
    acpi_root = fixture_root("thinkpad_acpi", "thinkpad-e16-gen2")
    identity = DmiSysfs(root=fixture_root("dmi", "thinkpad-e16-gen2"))
    provider = ThinkpadAcpiSysfs(root=acpi_root, identity=identity)

    assert provider.availability() is Availability.OK
    info = await provider.detect()
    assert info.is_thinkpad
    assert info.acpi_driver_loaded
    assert info.dmi_vendor_lenovo
    assert info.model == "ThinkPad E16 Gen 2"


async def test_qemu_vm_is_not_a_thinkpad() -> None:
    identity = DmiSysfs(root=fixture_root("dmi", "qemu-vm"))
    provider = ThinkpadAcpiSysfs(root=fixture_root("dmi", "qemu-vm"), identity=identity)

    info = await provider.detect()
    assert not info.is_thinkpad
    assert not info.acpi_driver_loaded
    assert not info.dmi_vendor_lenovo
    assert info.model is None


async def test_dmi_signal_alone_suffices(tmp_path: Path) -> None:
    # Lenovo DMI but no driver dir (e.g. driver blacklisted): still a ThinkPad.
    identity = DmiSysfs(root=fixture_root("dmi", "thinkpad-e16-gen2"))
    provider = ThinkpadAcpiSysfs(root=tmp_path, identity=identity)

    info = await provider.detect()
    assert info.is_thinkpad
    assert not info.acpi_driver_loaded
    assert info.model == "ThinkPad E16 Gen 2"


async def test_driver_signal_alone_suffices() -> None:
    provider = ThinkpadAcpiSysfs(
        root=fixture_root("thinkpad_acpi", "thinkpad-e16-gen2"), identity=None
    )
    info = await provider.detect()
    assert info.is_thinkpad
    assert info.acpi_driver_loaded
    assert info.model is None  # no identity port wired
