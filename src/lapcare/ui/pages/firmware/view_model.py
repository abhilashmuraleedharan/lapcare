# SPDX-License-Identifier: GPL-3.0-or-later
"""Firmware view-model: device list, metadata refresh, and the update flow.

Panel degradation policy: the device list (``list_devices``) is the page's
core — its failure fails the page (containers/CI: no fwupd daemon →
unavailable naming the fwupd package). One device's failed ``list_upgrades``
degrades to a note on that device only. A failed metadata refresh or a
declined polkit prompt is a toast, never a page state (ADR-0004).

Update-flow states (ROADMAP M3 UX criteria) are plain GObject properties the
view renders directly:
- ``busy_text``     non-empty while a refresh/install runs (actions disabled)
- ``flow_banner``   pre-commit precondition block, or install failure
                    (retry = the Install button stays available)
- ``reboot_banner`` non-empty when an applied update awaits a reboot
- ``result_text``   post-update "what changed" (release name/summary)
- ``toast_text``    transient notice (declined auth, refresh outcome)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from gettext import gettext as _
from typing import TYPE_CHECKING

from gi.repository import GLib, GObject

from lapcare.core.errors import (
    FirmwareInstallFailed,
    LapcareError,
    PrivilegedActionDenied,
)
from lapcare.core.firmware_policy import battery_ok_for_update
from lapcare.core.models import FirmwareDevice, FirmwareRelease, UpdateState
from lapcare.ui.pages.base_view_model import PageViewModel

if TYPE_CHECKING:
    from lapcare.core.ports import FirmwareProvider, Scheduler

log = logging.getLogger(__name__)

PLACEHOLDER = "—"
_RELOAD_DEBOUNCE_MS = 700

URGENCY_TEXT = {
    "critical": _("Critical"),
    "high": _("High priority"),
    "medium": _("Medium priority"),
    "low": _("Low priority"),
}

# Update states meaning "flashed, waiting for a reboot to take effect".
_REBOOT_PENDING_STATES = (UpdateState.NEEDS_REBOOT, UpdateState.PENDING)


@dataclass
class DeviceCard:
    """Finalized display data for one firmware device (view only copies it)."""

    id: str
    title: str
    subtitle: str
    version_text: str = PLACEHOLDER
    updatable: bool = False
    releases: list[FirmwareRelease] = field(default_factory=list)
    upgrade_note: str = ""  # per-device degradation ("" = upgrades listed fine)
    update_error: str = ""  # fwupd's record of this device's last failed update


class FirmwareViewModel(PageViewModel):
    __gtype_name__ = "LapcareFirmwareViewModel"

    busy_text = GObject.Property(type=str, default="")
    flow_banner = GObject.Property(type=str, default="")
    reboot_banner = GObject.Property(type=str, default="")
    result_text = GObject.Property(type=str, default="")
    toast_text = GObject.Property(type=str, default="")

    def __init__(self, scheduler: Scheduler, firmware: FirmwareProvider) -> None:
        super().__init__()
        self._scheduler = scheduler
        self._firmware = firmware
        self._reload_pending = False
        self._installing = False
        self.cards: list[DeviceCard] = []

    def load(self) -> None:
        self.show_loading()
        self._scheduler.submit(self._gather(), self._apply, self._load_failed)

    def _load_failed(self, exc: BaseException) -> None:
        # One greppable line for the smoke test (no fwupd in containers/CI).
        log.debug("firmware unavailable: %s", exc)
        self.handle_error(exc)

    def start_live_updates(self) -> None:
        """Subscribe to fwupd change signals; debounced reloads. Main thread only."""
        try:
            self._firmware.subscribe(self._on_changed)
        except LapcareError as exc:
            log.debug("no live updates: %s", exc)

    def _on_changed(self) -> None:
        # Installs emit a storm of DeviceChanged signals; the post-install
        # reload covers those, so skip reloads while one is running.
        if self._reload_pending or self._installing:
            return
        self._reload_pending = True

        def _reload() -> bool:
            self._reload_pending = False
            if not self._installing:
                self._scheduler.submit(self._gather(), self._apply, self._load_failed)
            return False  # GLib.SOURCE_REMOVE

        GLib.timeout_add(_RELOAD_DEBOUNCE_MS, _reload)

    async def _gather(self) -> list[tuple[FirmwareDevice, list[FirmwareRelease], str]]:
        devices = await self._firmware.list_devices()
        gathered: list[tuple[FirmwareDevice, list[FirmwareRelease], str]] = []
        for device in devices:
            releases: list[FirmwareRelease] = []
            note = ""
            if device.updatable:
                try:
                    releases = await self._firmware.list_upgrades(device.id)
                except LapcareError as exc:
                    # One device's upgrade query failing must not kill the page.
                    log.debug("upgrades degraded for %s: %s", device.id, exc)
                    note = _("Could not check for updates for this device.")
            gathered.append((device, releases, note))
        return gathered

    def _apply(self, data: list[tuple[FirmwareDevice, list[FirmwareRelease], str]]) -> None:
        if not data:
            log.debug("firmware unavailable: no devices reported")
            self.show_unavailable(
                _("fwupd reports no firmware devices on this system."),
                _("Nothing to do — no device exposes updatable firmware."),
            )
            return

        cards: list[DeviceCard] = []
        reboot_pending: list[str] = []
        for device, releases, note in data:
            subtitle = " · ".join(x for x in (device.vendor, device.plugin) if x)
            card = DeviceCard(
                id=device.id,
                title=device.name or device.id,
                subtitle=subtitle,
                version_text=device.version or PLACEHOLDER,
                updatable=device.updatable,
                releases=releases,
                upgrade_note=note,
                update_error=device.update_error or "",
            )
            cards.append(card)
            if device.update_state in _REBOOT_PENDING_STATES:
                reboot_pending.append(card.title)

        self.cards = cards
        self.props.reboot_banner = (
            _("Restart the system to finish updating: %s") % ", ".join(reboot_pending)
            if reboot_pending
            else ""
        )
        upgrades = sum(len(c.releases) for c in cards)
        log.debug("firmware ready devices=%d upgrades=%d", len(cards), upgrades)
        self.show_ready()

    # -- metadata refresh ---------------------------------------------------

    def refresh_metadata(self) -> None:
        if self.props.busy_text:
            return
        self.props.busy_text = _("Refreshing update metadata…")
        self._scheduler.submit(
            self._firmware.refresh_metadata(), self._refresh_done, self._refresh_failed
        )

    def _refresh_done(self, _result: None) -> None:
        self.props.busy_text = ""
        self.props.toast_text = _("Update metadata refreshed.")
        self._scheduler.submit(self._gather(), self._apply, self._load_failed)

    def _refresh_failed(self, exc: BaseException) -> None:
        # Refresh failure is a degradation (offline is normal), never a page error.
        log.debug("metadata refresh failed: %s", exc)
        self.props.busy_text = ""
        self.props.toast_text = _("Could not refresh update metadata — check your connection.")

    # -- install flow ---------------------------------------------------------

    def request_install(self, device_id: str, release: FirmwareRelease) -> None:
        """Start installing ``release`` on ``device_id`` (main thread only)."""
        if self.props.busy_text:
            return

        # Surface fwupd's battery precondition BEFORE committing (ROADMAP UX
        # criterion) instead of relaying its refusal after a download.
        level, threshold = self._firmware.battery_precondition()
        if not battery_ok_for_update(level, threshold):
            self.props.flow_banner = _(
                "Battery too low for a firmware update (%(level)d%%, needs %(threshold)d%%). "
                "Connect AC power and charge first."
            ) % {"level": level or 0, "threshold": threshold or 0}
            return

        self.props.flow_banner = ""
        self.props.result_text = ""
        self._installing = True
        self.props.busy_text = _("Installing firmware update…")
        self._scheduler.submit(
            self._firmware.install(device_id, release.version, self._on_progress),
            lambda _result: self._install_done(release),
            self._install_failed,
        )

    def _on_progress(self, percentage: int | None, status: str) -> None:
        if not self._installing:
            return
        text = _("Installing firmware update…") if not status else status.capitalize()
        if percentage is not None:
            text = f"{text} · {percentage}%"
        self.props.busy_text = text

    def _install_done(self, release: FirmwareRelease) -> None:
        self._installing = False
        self.props.busy_text = ""
        what = release.name or _("firmware update")
        self.props.result_text = (
            _("Updated to %(what)s %(version)s. %(summary)s")
            % {"what": what, "version": release.version, "summary": release.summary or ""}
        ).strip()
        # Reload recomputes the reboot banner from fwupd's update states.
        self._scheduler.submit(self._gather(), self._apply, self._load_failed)

    def _install_failed(self, exc: BaseException) -> None:
        self._installing = False
        self.props.busy_text = ""
        if isinstance(exc, PrivilegedActionDenied):
            # A legitimate choice: quiet degradation, never an error (ADR-0004).
            log.debug("install declined: %s", exc)
            self.props.toast_text = _("Firmware update cancelled.")
            return
        if isinstance(exc, FirmwareInstallFailed):
            log.warning("install failed: %s", exc)
            self.props.flow_banner = _("The firmware update failed: %s — you can retry.") % (
                exc.detail
            )
            self._scheduler.submit(self._gather(), self._apply, self._load_failed)
            return
        self.handle_error(exc)
