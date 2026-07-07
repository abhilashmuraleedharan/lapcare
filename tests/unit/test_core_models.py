# SPDX-License-Identifier: GPL-3.0-or-later
"""Core model/error sanity: frozen, optional-by-default, structured errors."""

from __future__ import annotations

import dataclasses

import pytest

from lapcare.core.errors import (
    LapcareError,
    PrivilegedActionDenied,
    ProviderParseError,
    ProviderTimeout,
    ProviderUnavailable,
)
from lapcare.core.models import Availability, SystemIdentity, ThinkpadInfo


def test_models_are_frozen() -> None:
    identity = SystemIdentity(vendor="LENOVO")
    with pytest.raises(dataclasses.FrozenInstanceError):
        identity.vendor = "other"  # type: ignore[misc]


def test_identity_fields_optional_by_default() -> None:
    identity = SystemIdentity()
    assert identity.vendor is None
    assert identity.bios_version is None


def test_thinkpad_info_minimal() -> None:
    info = ThinkpadInfo(is_thinkpad=False)
    assert not info.dmi_vendor_lenovo
    assert info.model is None


def test_provider_unavailable_carries_structure() -> None:
    exc = ProviderUnavailable("storage_smart", Availability.TOOL_MISSING, tool="smartmontools")
    assert isinstance(exc, LapcareError)
    assert exc.source == "storage_smart"
    assert exc.reason is Availability.TOOL_MISSING
    assert exc.tool == "smartmontools"
    assert "smartmontools" in str(exc)


def test_error_hierarchy() -> None:
    for exc in (
        ProviderTimeout("dmi", "read stalled"),
        ProviderParseError("pci_usb", "unexpected lspci line"),
        PrivilegedActionDenied("io.github.abhilashmuraleedharan.lapcare.smart-report"),
    ):
        assert isinstance(exc, LapcareError)
