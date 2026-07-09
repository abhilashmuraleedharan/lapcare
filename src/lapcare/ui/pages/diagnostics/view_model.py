# SPDX-License-Identifier: GPL-3.0-or-later
"""Diagnostics view-model: one-click run, explainable results, health score.

The page has no core data to load — it opens ready with a Run action and
renders whatever the last run produced. The Run action is privilege-marked
(it includes storage SMART via the ADR-0006 helper); a declined prompt
degrades that one signal to "not measured", never the run (ADR-0004).

All prose lives here (core carries data, not text): check ids, metric keys,
statuses, skip codes and confidence levels are translated through the tables
below, which the Dashboard's health card reuses.
"""

from __future__ import annotations

import contextlib
import datetime
import logging
import time
from dataclasses import dataclass, field
from gettext import gettext as _
from typing import TYPE_CHECKING

from gi.repository import GObject

from lapcare import __version__
from lapcare.core import diagnostics
from lapcare.core import report as core_report
from lapcare.core.errors import LapcareError
from lapcare.core.models import (
    CheckStatus,
    Confidence,
    DiagnosticsReport,
    OsInfo,
    SystemIdentity,
)
from lapcare.ui.pages.base_view_model import PageViewModel

if TYPE_CHECKING:
    from lapcare.core.ports import (
        BatteryWearProvider,
        DiskUsageProvider,
        FirmwareProvider,
        OsInfoProvider,
        ReportWriter,
        Scheduler,
        StorageProvider,
        SystemIdentityProvider,
        ThermalProvider,
    )

log = logging.getLogger(__name__)

CHECK_TITLES = {
    "battery-wear": _("Battery wear"),
    "storage-health": _("Storage health"),
    "firmware-currency": _("Firmware currency"),
    "thermal": _("Thermal sanity"),
    "disk-space": _("Disk space"),
}

STATUS_TEXT = {
    CheckStatus.OK: _("OK"),
    CheckStatus.WARNING: _("Warning"),
    CheckStatus.CRITICAL: _("Critical"),
    CheckStatus.SKIPPED: _("Not measured"),
}

STATUS_CSS = {
    CheckStatus.OK: "success",
    CheckStatus.WARNING: "warning",
    CheckStatus.CRITICAL: "error",
    CheckStatus.SKIPPED: "dim-label",
}

SKIP_TEXT = {
    "declined": _("Authorization was declined — run again to include it."),
    "unavailable": _("The data source is not available on this system."),
    "no-data": _("Nothing to measure on this machine."),
    "not-requested": _("Not included in this run."),
}

CONFIDENCE_TEXT = {
    Confidence.HIGH: _("high confidence"),
    Confidence.MEDIUM: _("medium confidence"),
    Confidence.LOW: _("low confidence"),
}

METRIC_LABELS = {
    "wear_pct": _("Worst battery wear"),
    "batteries": _("Batteries"),
    "failing_device": _("Failing device"),
    "pending_sectors": _("Sectors pending reallocation"),
    "endurance_used_pct": _("Rated endurance used"),
    "devices": _("Devices checked"),
    "pending_updates": _("Pending firmware updates"),
    "max_temp_c": _("Hottest sensor"),
    "max_temp_source": _("Hottest sensor source"),
    "sensors": _("Sensors read"),
    "min_free_pct": _("Least free space"),
    "min_free_mount": _("Fullest filesystem"),
    "critical_mount": _("Critically full filesystem"),
    "low_mount": _("Low-space filesystem"),
}


def _metric_value(key: str, value: str) -> str:
    if key.endswith("_pct"):
        return f"{value}%"
    if key.endswith("_c"):
        return _("%s °C") % value
    return value


@dataclass
class CheckCard:
    """Finalized display data for one check (view only copies it)."""

    check_id: str
    title: str
    status_text: str
    status_css: str
    subtitle: str  # confidence, or the skip explanation
    evidence: list[tuple[str, str]] = field(default_factory=list)


def result_cards(report: DiagnosticsReport) -> list[CheckCard]:
    cards = []
    for result in report.results:
        if result.status is CheckStatus.SKIPPED:
            subtitle = SKIP_TEXT.get(result.skip_code, SKIP_TEXT["unavailable"])
        else:
            subtitle = CONFIDENCE_TEXT[result.confidence]
        cards.append(
            CheckCard(
                check_id=result.check_id,
                title=CHECK_TITLES.get(result.check_id, result.check_id),
                status_text=STATUS_TEXT[result.status],
                status_css=STATUS_CSS[result.status],
                subtitle=subtitle,
                evidence=[
                    (METRIC_LABELS.get(key, key), _metric_value(key, value))
                    for key, value in result.metrics
                ],
            )
        )
    return cards


def _system_rows(identity: SystemIdentity | None, os_info: OsInfo | None) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if identity is not None:
        for label, value in (
            (_("Model"), identity.product_family),
            (_("Machine type"), identity.product_name),
            (_("Vendor"), identity.vendor),
            (_("BIOS / UEFI"), identity.bios_version),
        ):
            if value:
                rows.append((label, value.strip()))
    if os_info is not None:
        for label, value in (
            (_("Operating system"), os_info.distro_name),
            (_("Kernel"), os_info.kernel),
        ):
            if value:
                rows.append((label, value))
    return rows


def score_texts(report: DiagnosticsReport) -> tuple[str, str]:
    """(headline, coverage) for a score display — shared with the Dashboard."""
    headline = _("%d / 100") % report.score if report.score is not None else _("No score")
    coverage = _("Experimental — based on %(measured)d of %(total)d signals") % {
        "measured": report.measured,
        "total": report.total,
    }
    return headline, coverage


class DiagnosticsViewModel(PageViewModel):
    __gtype_name__ = "LapcareDiagnosticsViewModel"

    busy_text = GObject.Property(type=str, default="")
    score_text = GObject.Property(type=str, default="")
    coverage_text = GObject.Property(type=str, default="")
    toast_text = GObject.Property(type=str, default="")

    def __init__(
        self,
        scheduler: Scheduler,
        *,
        battery_wear: BatteryWearProvider,
        storage: StorageProvider,
        firmware: FirmwareProvider,
        thermal: ThermalProvider,
        disk: DiskUsageProvider,
        identity: SystemIdentityProvider | None = None,
        os_info: OsInfoProvider | None = None,
        writer: ReportWriter | None = None,
    ) -> None:
        super().__init__()
        self._scheduler = scheduler
        self._battery_wear = battery_wear
        self._storage = storage
        self._firmware = firmware
        self._thermal = thermal
        self._disk = disk
        self._identity = identity
        self._os_info = os_info
        self._writer = writer
        self._last_report: DiagnosticsReport | None = None
        self.cards: list[CheckCard] = []

    @property
    def can_export(self) -> bool:
        return self._writer is not None and self._last_report is not None

    def load(self) -> None:
        # No core data to fetch: the page opens ready, awaiting a run.
        log.debug("diagnostics ready (idle)")
        self.show_ready()

    def run(self) -> None:
        """One click, every check; SMART included (the button is
        privilege-marked). Main thread only."""
        if self.props.busy_text:
            return
        self.props.busy_text = _("Running diagnostics…")
        self._scheduler.submit(self._timed_run(), self._run_done, self._run_failed)

    async def _timed_run(self) -> tuple[DiagnosticsReport, float]:
        started = time.monotonic()
        report = await diagnostics.run(
            battery_wear=self._battery_wear,
            storage=self._storage,
            firmware=self._firmware,
            thermal=self._thermal,
            disk=self._disk,
            include_storage_health=True,
        )
        return report, time.monotonic() - started

    def _run_done(self, outcome: tuple[DiagnosticsReport, float]) -> None:
        report, elapsed = outcome
        self.props.busy_text = ""
        self._last_report = report
        self.cards = result_cards(report)
        headline, coverage = score_texts(report)
        self.props.score_text = headline
        self.props.coverage_text = coverage
        # The <10s acceptance criterion, greppable in --verbose runs.
        log.debug(
            "diagnostics completed in %.1fs score=%s measured=%d/%d",
            elapsed,
            report.score,
            report.measured,
            report.total,
        )
        self.show_ready()

    def _run_failed(self, exc: BaseException) -> None:
        # run() degrades per source and should never raise; anything here is
        # unexpected and belongs on the error page with detail.
        self.props.busy_text = ""
        log.warning("diagnostics run failed: %s", exc)
        self.handle_error(exc)

    # -- report export (redacted by default — core/report.py) -----------------

    def export(self, path: str) -> None:
        """Write the last run's report to ``path``; the extension picks the
        format (.json machine-readable, .html, anything else Markdown)."""
        if not self.can_export or self.props.busy_text:
            return
        self.props.busy_text = _("Exporting report…")
        self._scheduler.submit(self._render_and_write(path), self._export_done, self._export_failed)

    async def _render_and_write(self, path: str) -> str:
        assert self._last_report is not None and self._writer is not None
        identity: SystemIdentity | None = None
        os_info: OsInfo | None = None
        # A report without system context is still a report.
        if self._identity is not None:
            with contextlib.suppress(LapcareError):
                identity = await self._identity.read_identity()
        if self._os_info is not None:
            with contextlib.suppress(LapcareError):
                os_info = await self._os_info.read_os()
        generated = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M UTC")

        if path.endswith(".json"):
            content = core_report.to_json(
                generated=generated,
                app_version=__version__,
                identity=identity,
                os_info=os_info,
                diagnostics=self._last_report,
            )
        else:
            # Deferred import: keeps the renderers out of every page load.
            from lapcare.ui.pages.diagnostics import report_render

            system_rows = _system_rows(identity, os_info)
            render = (
                report_render.render_html
                if path.endswith(".html")
                else report_render.render_markdown
            )
            content = render(
                generated=generated,
                app_version=__version__,
                system_rows=system_rows,
                score_text=self.props.score_text,
                coverage_text=self.props.coverage_text,
                cards=self.cards,
            )
        self._writer.write(path, content)
        return path

    def _export_done(self, path: str) -> None:
        self.props.busy_text = ""
        log.debug("report exported")  # never log the path (may name the user)
        self.props.toast_text = _("Report exported.")

    def _export_failed(self, exc: BaseException) -> None:
        self.props.busy_text = ""
        log.warning("report export failed: %s", type(exc).__name__)
        self.props.toast_text = _("Could not export the report.")
