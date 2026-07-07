# SPDX-License-Identifier: GPL-3.0-or-later
"""os_info provider against fixture roots: full, sparse, and absent."""

from __future__ import annotations

from pathlib import Path

from lapcare.core.models import Availability
from lapcare.providers.os_info import OsInfoProc, _parse_os_release

from .conftest import fixture_root


async def test_full_fixture() -> None:
    provider = OsInfoProc(root=fixture_root("os_info", "synthetic-full"))
    assert provider.availability() is Availability.OK

    os_info = await provider.read_os()
    assert os_info.distro_name == "Ubuntu 24.04.2 LTS"
    assert os_info.distro_version == "24.04"
    assert os_info.kernel == "6.8.0-124-generic"
    assert os_info.hostname == "fixture-host"
    assert os_info.uptime_seconds == 123456.78

    cpu_mem = await provider.read_cpu_mem()
    assert cpu_mem.cpu_model == "AMD Ryzen 7 7735HS with Radeon Graphics"
    assert cpu_mem.cpu_count == 2
    assert cpu_mem.memory_total_kib == 15980414


async def test_sparse_fixture_degrades_to_none() -> None:
    provider = OsInfoProc(root=fixture_root("os_info", "synthetic-sparse"))
    assert provider.availability() is Availability.OK

    os_info = await provider.read_os()
    assert os_info.distro_name is None
    assert os_info.kernel is None
    assert os_info.uptime_seconds is None  # file present but garbage

    cpu_mem = await provider.read_cpu_mem()
    assert cpu_mem.cpu_model is None
    assert cpu_mem.cpu_count is None
    assert cpu_mem.memory_total_kib is None


async def test_absent_root_is_unsupported(tmp_path: Path) -> None:
    provider = OsInfoProc(root=tmp_path / "nowhere")
    assert provider.availability() is Availability.UNSUPPORTED_HARDWARE
    # Reads still never raise — they degrade.
    assert (await provider.read_os()).kernel is None


def test_os_release_parser_tolerates_junk() -> None:
    parsed = _parse_os_release('A=1\n# comment\nBROKEN LINE\nB="two words"\n\n')
    assert parsed == {"A": "1", "B": "two words"}
