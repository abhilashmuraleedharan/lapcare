# SPDX-License-Identifier: GPL-3.0-or-later
"""Storage view-model: unprivileged inventory + on-demand SMART health.

Panel degradation policy: the inventory (``list_devices``, /sys/block) is the
page's core — its failure fails the page. Health is an explicit, visually
privilege-marked action (ADR-0004/ADR-0006): a declined polkit prompt or a
missing helper/smartmontools is a toast, never a page state, and the
inventory keeps rendering. One device's failed SMART read degrades to a note
on that device only; ``PrivilegedActionDenied`` and ``ProviderUnavailable``
abort the whole run (they would repeat identically for every device).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from gettext import gettext as _
from typing import TYPE_CHECKING

from gi.repository import GObject

from lapcare.core.errors import (
    LapcareError,
    PrivilegedActionDenied,
    ProviderUnavailable,
)
from lapcare.core.models import SmartReport, StorageDevice
from lapcare.ui.pages.base_view_model import PageViewModel

if TYPE_CHECKING:
    from lapcare.core.ports import Scheduler, StorageProvider

log = logging.getLogger(__name__)


def _size_text(size_bytes: int | None) -> str:
    """Decimal units, matching how drives are marketed (512 GB, not GiB)."""
    if size_bytes is None:
        return ""
    if size_bytes >= 1000**4:
        return _("%.1f TB") % (size_bytes / 1000**4)
    if size_bytes >= 1000**3:
        return _("%.1f GB") % (size_bytes / 1000**3)
    return _("%.0f MB") % (size_bytes / 1000**2)


def _kind_text(device: StorageDevice) -> str:
    if device.name.startswith("nvme"):
        kind = _("NVMe SSD")
    elif device.rotational is False:
        kind = _("SSD")
    elif device.rotational:
        kind = _("Hard disk")
    else:
        kind = _("Disk")
    if device.removable:
        kind = _("%s (removable)") % kind
    return kind


@dataclass
class StorageCard:
    """Finalized display data for one block device (view only copies it)."""

    name: str  # kernel name — the read_smart argument
    title: str
    subtitle: str
    health_summary: str = ""  # "" until health was read for this device
    health_failed: bool = False  # drives the destructive style on the row
    health_rows: list[tuple[str, str]] = field(default_factory=list)
    health_note: str = ""  # per-device degradation


class StorageViewModel(PageViewModel):
    __gtype_name__ = "LapcareStorageViewModel"

    busy_text = GObject.Property(type=str, default="")
    toast_text = GObject.Property(type=str, default="")

    def __init__(self, scheduler: Scheduler, storage: StorageProvider) -> None:
        super().__init__()
        self._scheduler = scheduler
        self._storage = storage
        self.cards: list[StorageCard] = []

    def load(self) -> None:
        self.show_loading()
        self._scheduler.submit(self._storage.list_devices(), self._apply, self._load_failed)

    def _load_failed(self, exc: BaseException) -> None:
        # One greppable line for the smoke test.
        log.debug("storage unavailable: %s", exc)
        self.handle_error(exc)

    def _apply(self, devices: list[StorageDevice]) -> None:
        if not devices:
            log.debug("storage unavailable: no physical block devices")
            self.show_unavailable(
                _("No storage devices found."),
                _("Nothing to do — no physical disk is visible to this system."),
            )
            return
        self.cards = [
            StorageCard(
                name=device.name,
                title=device.model or device.name,
                subtitle=" · ".join(
                    x for x in (_size_text(device.size_bytes), _kind_text(device), device.name) if x
                ),
            )
            for device in devices
        ]
        log.debug("storage ready devices=%d", len(self.cards))
        self.show_ready()

    # -- SMART health (privileged, explicit action — ADR-0006) ----------------

    def read_health(self) -> None:
        """Read SMART for every device; ONE polkit prompt (auth_admin_keep)."""
        if self.props.busy_text or not self.cards:
            return
        self.props.busy_text = _("Reading storage health…")
        names = [card.name for card in self.cards]
        self._scheduler.submit(self._gather_health(names), self._health_done, self._health_failed)

    async def _gather_health(self, names: list[str]) -> list[tuple[str, SmartReport | None, str]]:
        results: list[tuple[str, SmartReport | None, str]] = []
        for name in names:
            try:
                results.append((name, await self._storage.read_smart(name), ""))
            except PrivilegedActionDenied:
                raise  # would re-prompt identically for every device
            except ProviderUnavailable:
                raise  # missing helper/smartmontools affects every device
            except LapcareError as exc:
                log.debug("smart degraded for %s: %s", name, exc)
                results.append((name, None, _("Could not read health for this device.")))
        return results

    def _health_done(self, results: list[tuple[str, SmartReport | None, str]]) -> None:
        self.props.busy_text = ""
        by_name = {name: (report, note) for name, report, note in results}
        for card in self.cards:
            report, note = by_name.get(card.name, (None, ""))
            card.health_note = note
            if report is not None:
                card.health_summary, card.health_failed = _summary(report)
                card.health_rows = _health_rows(report)
        # Cards changed in place; re-announce ready so the view rebuilds.
        self.show_ready()

    def _health_failed(self, exc: BaseException) -> None:
        self.props.busy_text = ""
        if isinstance(exc, PrivilegedActionDenied):
            # A legitimate choice: quiet degradation, never an error (ADR-0004).
            log.debug("smart read declined: %s", exc)
            self.props.toast_text = _("Storage health check cancelled.")
            return
        if isinstance(exc, ProviderUnavailable):
            log.debug("smart unavailable: %s", exc)
            self.props.toast_text = (
                _("Storage health needs the '%s' package.") % exc.tool
                if exc.tool
                else _("Storage health reading is not available on this system.")
            )
            return
        log.warning("smart read failed: %s", exc)
        self.props.toast_text = _("Could not read storage health.")


def _summary(report: SmartReport) -> tuple[str, bool]:
    if report.passed is False:
        return _("FAILING — back up your data now"), True
    if report.passed is True:
        return _("Healthy"), False
    return _("Health not reported"), False


def _health_rows(report: SmartReport) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []

    def add(label: str, value: str | None) -> None:
        if value is not None:
            rows.append((label, value))

    if report.temperature_c is not None:
        add(_("Temperature"), _("%d °C") % report.temperature_c)
    if report.percentage_used is not None:
        add(_("Rated endurance used"), f"{report.percentage_used}%")
    if report.available_spare_pct is not None:
        add(_("Spare capacity available"), f"{report.available_spare_pct}%")
    if report.media_errors is not None:
        add(_("Media errors"), str(report.media_errors))
    if report.reallocated_sectors is not None:
        add(_("Reallocated sectors"), str(report.reallocated_sectors))
    if report.pending_sectors is not None:
        add(_("Sectors pending reallocation"), str(report.pending_sectors))
    if report.power_on_hours is not None:
        add(_("Powered on"), _("%d hours") % report.power_on_hours)
    if report.power_cycles is not None:
        add(_("Power cycles"), str(report.power_cycles))
    if report.unsafe_shutdowns is not None:
        add(_("Unsafe shutdowns"), str(report.unsafe_shutdowns))
    if report.firmware_version is not None:
        add(_("Firmware"), report.firmware_version)
    if report.messages:
        # Data-quality notes (e.g. the E16's NVMe lacks a self-test log).
        add(_("Notes"), "; ".join(report.messages))
    return rows
