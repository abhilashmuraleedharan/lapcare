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

from lapcare.core.models import OsInfo, SystemIdentity, ThinkpadInfo
from lapcare.ui.pages.base_view_model import PageViewModel

if TYPE_CHECKING:
    from lapcare.core.ports import (
        OsInfoProvider,
        Scheduler,
        SystemIdentityProvider,
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

    def __init__(
        self,
        scheduler: Scheduler,
        identity: SystemIdentityProvider,
        os_info: OsInfoProvider,
        thinkpad: ThinkpadProvider,
    ) -> None:
        super().__init__()
        self._scheduler = scheduler
        self._identity = identity
        self._os_info = os_info
        self._thinkpad = thinkpad

    def load(self) -> None:
        self.show_loading()
        self._scheduler.submit(self._gather(), self._apply, self.handle_error)

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

        log.debug("dashboard ready model=%s thinkpad=%s", self.props.model, thinkpad.is_thinkpad)
        self.show_ready()
