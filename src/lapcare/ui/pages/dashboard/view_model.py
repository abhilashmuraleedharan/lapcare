# SPDX-License-Identifier: GPL-3.0-or-later
"""Dashboard view-model: identity + OS overview + ThinkPad detection.

Receives ports and the scheduler from the composition root (app.py); never
constructs providers. Display strings are finalized here so the view only
copies them into rows.
"""

from __future__ import annotations

import logging
from gettext import gettext as _
from typing import TYPE_CHECKING

from gi.repository import GObject

from lapcare.core import diagnostics
from lapcare.core.models import DiagnosticsReport, OsInfo, SystemIdentity, ThinkpadInfo
from lapcare.ui.pages.base_view_model import PageViewModel
from lapcare.ui.pages.diagnostics.view_model import score_texts

if TYPE_CHECKING:
    from lapcare.core.ports import (
        BatteryWearProvider,
        DiskUsageProvider,
        FirmwareProvider,
        OsInfoProvider,
        Scheduler,
        SystemIdentityProvider,
        ThermalProvider,
        ThinkpadProvider,
    )

log = logging.getLogger(__name__)

PLACEHOLDER = "—"


def format_uptime(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return PLACEHOLDER
    minutes = int(seconds // 60)
    days, rest = divmod(minutes, 24 * 60)
    hours, mins = divmod(rest, 60)
    if days:
        return _("%(d)dd %(h)dh %(m)dm") % {"d": days, "h": hours, "m": mins}
    if hours:
        return _("%(h)dh %(m)dm") % {"h": hours, "m": mins}
    return _("%(m)dm") % {"m": mins}


class DashboardViewModel(PageViewModel):
    __gtype_name__ = "LapcareDashboardViewModel"

    model = GObject.Property(type=str, default=PLACEHOLDER)
    machine_type = GObject.Property(type=str, default=PLACEHOLDER)
    vendor = GObject.Property(type=str, default=PLACEHOLDER)
    bios = GObject.Property(type=str, default=PLACEHOLDER)
    distro = GObject.Property(type=str, default=PLACEHOLDER)
    kernel = GObject.Property(type=str, default=PLACEHOLDER)
    uptime = GObject.Property(type=str, default=PLACEHOLDER)
    is_thinkpad = GObject.Property(type=bool, default=True)  # banner hidden until known
    health_score = GObject.Property(type=str, default="")  # "" = no score card yet
    health_coverage = GObject.Property(type=str, default="")

    def __init__(
        self,
        scheduler: Scheduler,
        identity: SystemIdentityProvider,
        os_info: OsInfoProvider,
        thinkpad: ThinkpadProvider,
        *,
        battery_wear: BatteryWearProvider | None = None,
        firmware: FirmwareProvider | None = None,
        thermal: ThermalProvider | None = None,
        disk: DiskUsageProvider | None = None,
    ) -> None:
        super().__init__()
        self._scheduler = scheduler
        self._identity = identity
        self._os_info = os_info
        self._thinkpad = thinkpad
        self._battery_wear = battery_wear
        self._firmware = firmware
        self._thermal = thermal
        self._disk = disk

    def load(self) -> None:
        self.show_loading()
        self._scheduler.submit(self._gather(), self._apply, self.handle_error)
        # The health score loads independently so a slow signal source never
        # delays the identity rows. Unprivileged only: storage SMART is never
        # read from the Dashboard (zero prompts here — ADR-0004); its signal
        # counts as unmeasured coverage instead.
        self._scheduler.submit(
            diagnostics.run(
                battery_wear=self._battery_wear,
                storage=None,
                firmware=self._firmware,
                thermal=self._thermal,
                disk=self._disk,
            ),
            self._apply_health,
            self._health_failed,
        )

    def _apply_health(self, report: DiagnosticsReport) -> None:
        if report.score is None:
            # Nothing measurable: no card beats a card that says nothing.
            log.debug("health score unavailable: no signal measured")
            return
        headline, coverage = score_texts(report)
        self.props.health_coverage = coverage
        self.props.health_score = headline
        log.debug("health score=%s measured=%d/%d", report.score, report.measured, report.total)

    def _health_failed(self, exc: BaseException) -> None:
        # The score is a bonus card: without it the dashboard is still whole.
        log.debug("health score unavailable: %s", exc)

    async def _gather(self) -> tuple[SystemIdentity, OsInfo, ThinkpadInfo]:
        return (
            await self._identity.read_identity(),
            await self._os_info.read_os(),
            await self._thinkpad.detect(),
        )

    def _apply(self, data: tuple[SystemIdentity, OsInfo, ThinkpadInfo]) -> None:
        identity, os_info, thinkpad = data

        self.props.model = thinkpad.model or identity.product_family or PLACEHOLDER
        self.props.machine_type = identity.product_name or PLACEHOLDER
        self.props.vendor = identity.vendor or PLACEHOLDER
        if identity.bios_version:
            self.props.bios = identity.bios_version.strip() + (
                f" ({identity.bios_date})" if identity.bios_date else ""
            )
        distro = os_info.distro_name or PLACEHOLDER
        self.props.distro = distro
        self.props.kernel = os_info.kernel or PLACEHOLDER
        self.props.uptime = format_uptime(os_info.uptime_seconds)
        self.props.is_thinkpad = thinkpad.is_thinkpad

        from lapcare import launch_elapsed_s

        # "First meaningful dashboard content" — the ROADMAP M5 launch metric.
        log.info(
            "dashboard ready model=%s thinkpad=%s elapsed=%.3fs",
            self.props.model,
            thinkpad.is_thinkpad,
            launch_elapsed_s() or -1.0,
        )
        self.show_ready()
