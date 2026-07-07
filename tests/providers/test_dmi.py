# SPDX-License-Identifier: GPL-3.0-or-later
"""dmi provider against real (E16 Gen 2) and VM fixtures."""

from __future__ import annotations

from pathlib import Path

from lapcare.core.models import Availability
from lapcare.providers.dmi import DmiSysfs

from .conftest import fixture_root


async def test_e16_gen2_real_capture() -> None:
    provider = DmiSysfs(root=fixture_root("dmi", "thinkpad-e16-gen2"))
    assert provider.availability() is Availability.OK

    identity = await provider.read_identity()
    assert identity.vendor == "LENOVO"
    assert identity.product_name == "21MBCTO1WW"
    assert identity.product_family == "ThinkPad E16 Gen 2"
    assert identity.product_version == "ThinkPad E16 Gen 2"
    assert identity.board_name == "21MBCTO1WW"
    assert identity.bios_version == "R2JET48W(1.25 )"  # trailing space is real
    assert identity.bios_date == "04/27/2026"
    # product_serial absent from the fixture (unreadable unprivileged) -> None
    assert identity.serial is None


async def test_qemu_vm_is_not_lenovo_but_valid() -> None:
    provider = DmiSysfs(root=fixture_root("dmi", "qemu-vm"))
    assert provider.availability() is Availability.OK

    identity = await provider.read_identity()
    assert identity.vendor == "QEMU"
    assert identity.product_family is None  # VM exposes fewer fields
    assert identity.bios_version is None


async def test_no_dmi_directory_is_unsupported(tmp_path: Path) -> None:
    provider = DmiSysfs(root=tmp_path)
    assert provider.availability() is Availability.UNSUPPORTED_HARDWARE
    identity = await provider.read_identity()  # still never raises
    assert identity.vendor is None
