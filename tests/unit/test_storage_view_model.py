# SPDX-License-Identifier: GPL-3.0-or-later
"""Storage view-model: states, health flow, and ADR-0004 quiet degradation."""

from __future__ import annotations

from lapcare.core.errors import (
    PrivilegedActionDenied,
    ProviderParseError,
    ProviderUnavailable,
)
from lapcare.core.models import Availability, SmartReport, StorageDevice
from lapcare.ui.pages.storage.view_model import StorageViewModel

from .test_dashboard_view_model import ImmediateScheduler

NVME = StorageDevice(
    name="nvme0n1",
    model="SKHynix_HFS512GEM4X169N",
    size_bytes=512110190592,
    removable=False,
    rotational=False,
)
NVME_REPORT = SmartReport(
    device_name="nvme0n1",
    passed=True,
    temperature_c=43,
    percentage_used=2,
    available_spare_pct=100,
    media_errors=0,
    power_on_hours=278,
    serial_number="REDACTED0000000000",
    messages=("Read Self-test Log failed: Invalid Field in Command (0x002)",),
)
FAILING_REPORT = SmartReport(device_name="sda", passed=False, reallocated_sectors=1264)


class FakeStorage:
    def __init__(
        self,
        devices: list[StorageDevice] | None = None,
        reports: dict[str, SmartReport] | None = None,
    ) -> None:
        self.devices = devices
        self.reports = reports or {}
        self.smart_error: Exception | None = None
        self.smart_calls: list[str] = []

    def availability(self) -> Availability:
        return Availability.OK

    async def list_devices(self) -> list[StorageDevice]:
        if self.devices is None:
            raise ProviderUnavailable("storage_smart", Availability.UNSUPPORTED_HARDWARE)
        return self.devices

    async def read_smart(self, device_name: str) -> SmartReport:
        self.smart_calls.append(device_name)
        if self.smart_error is not None:
            raise self.smart_error
        if device_name not in self.reports:
            raise ProviderParseError("storage_smart", "helper: unknown-device")
        return self.reports[device_name]


def _vm(storage: FakeStorage) -> StorageViewModel:
    return StorageViewModel(ImmediateScheduler(), storage=storage)


def test_inventory_renders_without_any_privileged_call() -> None:
    fake = FakeStorage([NVME])
    vm = _vm(fake)
    vm.load()
    assert vm.props.state == "ready"
    assert fake.smart_calls == []  # zero prompts before the explicit action
    (card,) = vm.cards
    assert card.title == "SKHynix_HFS512GEM4X169N"
    assert "512.1 GB" in card.subtitle
    assert "NVMe SSD" in card.subtitle
    assert card.health_rows == []


def test_zero_devices_is_unavailable_nothing_to_do() -> None:
    vm = _vm(FakeStorage([]))
    vm.load()
    assert vm.props.state == "unavailable"
    assert "Nothing to do" in vm.props.unavailable_remedy


def test_inventory_failure_fails_the_page() -> None:
    vm = _vm(FakeStorage(devices=None))
    vm.load()
    assert vm.props.state == "unavailable"


def test_read_health_fills_rows_and_notes_quirks() -> None:
    vm = _vm(FakeStorage([NVME], {"nvme0n1": NVME_REPORT}))
    vm.load()
    vm.read_health()
    assert vm.props.state == "ready"
    assert vm.props.busy_text == ""
    (card,) = vm.cards
    assert card.health_summary == "Healthy"
    assert not card.health_failed
    labels = dict(card.health_rows)
    assert labels["Temperature"] == "43 °C"
    assert labels["Rated endurance used"] == "2%"
    assert "Self-test Log" in labels["Notes"]  # the E16 data-quality quirk
    # The serial is an identifier (ADR-0006 §17): never in display rows.
    assert all("REDACTED0000000000" not in v for v in labels.values())


def test_failing_disk_is_marked() -> None:
    sda = StorageDevice(name="sda", model="SYNTH SSD", rotational=False)
    vm = _vm(FakeStorage([sda], {"sda": FAILING_REPORT}))
    vm.load()
    vm.read_health()
    (card,) = vm.cards
    assert card.health_failed
    assert "back up" in card.health_summary


def test_one_device_smart_failure_degrades_to_note() -> None:
    sda = StorageDevice(name="sda")
    vm = _vm(FakeStorage([NVME, sda], {"nvme0n1": NVME_REPORT}))
    vm.load()
    vm.read_health()
    assert vm.props.state == "ready"
    nvme_card, sda_card = vm.cards
    assert nvme_card.health_summary == "Healthy"
    assert sda_card.health_note != ""
    assert sda_card.health_rows == []


def test_declined_auth_is_quiet_toast_and_single_attempt() -> None:
    fake = FakeStorage([NVME, StorageDevice(name="sda")])
    fake.smart_error = PrivilegedActionDenied(
        "io.github.abhilashmuraleedharan.lapcare.smart-report"
    )
    vm = _vm(fake)
    vm.load()
    vm.read_health()
    assert vm.props.state == "ready"  # never an error page (ADR-0004)
    assert vm.props.toast_text != ""
    assert fake.smart_calls == ["nvme0n1"]  # aborted: no second prompt
    assert all(c.health_rows == [] for c in vm.cards)


def test_missing_helper_is_toast_naming_the_package() -> None:
    fake = FakeStorage([NVME])
    fake.smart_error = ProviderUnavailable(
        "storage_smart", Availability.TOOL_MISSING, tool="smartmontools"
    )
    vm = _vm(fake)
    vm.load()
    vm.read_health()
    assert vm.props.state == "ready"
    assert "smartmontools" in vm.props.toast_text
