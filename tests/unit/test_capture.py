# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture tool: layout, capture-time redaction, opt-in identifiers."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from lapcare.capture import capture


def _make_source_root(root: Path) -> None:
    dmi = root / "sys/class/dmi/id"
    dmi.mkdir(parents=True)
    (dmi / "sys_vendor").write_text("LENOVO\n")
    (dmi / "product_family").write_text("ThinkPad E16 Gen 2\n")
    (dmi / "bios_version").write_text("R2JET48W(1.25 )\n")
    (dmi / "product_serial").write_text("SECRET123\n")
    (dmi / "product_uuid").write_text("11111111-2222-3333-4444-555555555555\n")

    kernel = root / "proc/sys/kernel"
    kernel.mkdir(parents=True)
    (kernel / "hostname").write_text("my-private-hostname\n")
    (kernel / "osrelease").write_text("6.8.0-124-generic\n")
    (root / "etc").mkdir()
    (root / "etc/os-release").write_text('PRETTY_NAME="Ubuntu 24.04.2 LTS"\n')
    (root / "proc/uptime").write_text("100.0 200.0\n")

    tp = root / "sys/devices/platform/thinkpad_acpi"
    tp.mkdir(parents=True)
    (tp / "uevent").write_text("DRIVER=thinkpad_acpi\n")
    (tp / "fan").write_text("level: auto\n")


async def _fake_runner(tool: str, args: Sequence[str], *, timeout: float = 10.0) -> str:
    return f"fake {tool} output\n"


async def test_capture_redacts_by_default(tmp_path: Path) -> None:
    source, out = tmp_path / "source", tmp_path / "out"
    _make_source_root(source)

    machine = await capture(out, root=source, runner=_fake_runner)
    assert machine == "thinkpad-e16-gen-2"

    dmi_out = out / "dmi" / machine / "sys/class/dmi/id"
    assert (dmi_out / "sys_vendor").read_text().strip() == "LENOVO"
    assert (dmi_out / "bios_version").read_text().strip() == "R2JET48W(1.25 )"
    assert not (dmi_out / "product_serial").exists()
    assert not (dmi_out / "product_uuid").exists()

    hostname = out / "os_info" / machine / "proc/sys/kernel/hostname"
    assert hostname.read_text().strip() == "redacted-host"

    # Nothing anywhere in the capture contains the identifiers.
    all_text = "".join(p.read_text() for p in out.rglob("*") if p.is_file())
    assert "SECRET123" not in all_text
    assert "my-private-hostname" not in all_text

    assert (out / "thinkpad_acpi" / machine / "sys/devices/platform/thinkpad_acpi/uevent").exists()
    names = (
        out
        / "thinkpad_acpi"
        / machine
        / "sys/devices/platform/thinkpad_acpi"
        / "attribute-names.txt"
    ).read_text()
    assert "fan" in names

    assert (out / "pci_usb" / machine / "lspci.txt").read_text() == "fake lspci output\n"
    assert "redacted at capture time" in (out / "README.md").read_text()


async def test_capture_identifiers_opt_in(tmp_path: Path) -> None:
    source, out = tmp_path / "source", tmp_path / "out"
    _make_source_root(source)

    machine = await capture(out, root=source, runner=_fake_runner, include_identifiers=True)

    dmi_out = out / "dmi" / machine / "sys/class/dmi/id"
    assert (dmi_out / "product_serial").read_text().strip() == "SECRET123"
    hostname = out / "os_info" / machine / "proc/sys/kernel/hostname"
    assert hostname.read_text().strip() == "my-private-hostname"
    assert "IDENTIFIERS INCLUDED" in (out / "README.md").read_text()


async def test_capture_tolerates_missing_tools(tmp_path: Path) -> None:
    source, out = tmp_path / "source", tmp_path / "out"
    _make_source_root(source)

    async def broken_runner(tool: str, args: Sequence[str], *, timeout: float = 10.0) -> str:
        raise RuntimeError("no such tool")

    machine = await capture(out, root=source, runner=broken_runner)
    assert not (out / "pci_usb" / machine / "lspci.txt").exists()
    assert "not captured" in (out / "README.md").read_text()
