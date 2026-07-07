# SPDX-License-Identifier: GPL-3.0-or-later
"""PageViewModel: the base every page view-model extends.

Owns the four-state contract (state property + transitions) and the single
place core errors become user-facing text. Views bind to `state` and the
detail properties; subclasses add data properties and async loading via the
platform scheduler. Display-free and testable: plain GObject, no widgets.
"""

from __future__ import annotations

import logging
from gettext import gettext as _

from gi.repository import GObject

from lapcare.core.errors import (
    ProviderParseError,
    ProviderTimeout,
    ProviderUnavailable,
)
from lapcare.core.models import Availability

log = logging.getLogger(__name__)

STATES = ("loading", "ready", "unavailable", "error")


class PageViewModel(GObject.Object):
    state = GObject.Property(type=str, default="loading")
    unavailable_reason = GObject.Property(type=str, default="")
    unavailable_remedy = GObject.Property(type=str, default="")
    error_detail = GObject.Property(type=str, default="")

    def show_loading(self) -> None:
        self.props.state = "loading"

    def show_ready(self) -> None:
        self.props.state = "ready"

    def show_unavailable(self, reason: str, remedy: str) -> None:
        # Unavailable states always name the remedy (STYLEGUIDE).
        self.props.unavailable_reason = reason
        self.props.unavailable_remedy = remedy
        self.props.state = "unavailable"

    def show_error(self, detail: str) -> None:
        self.props.error_detail = detail
        self.props.state = "error"

    def handle_error(self, exc: BaseException) -> None:
        """Map a core error to the right page state with translated text."""
        if isinstance(exc, ProviderUnavailable):
            if exc.reason is Availability.TOOL_MISSING:
                reason = _("This panel needs a tool that is not installed.")
                remedy = (
                    _("Install the '%s' package to enable it.") % exc.tool
                    if exc.tool
                    else _("Install the missing tool to enable it.")
                )
            elif exc.reason is Availability.PERMISSION_DENIED:
                reason = _("Lapcare does not have permission to read this data.")
                remedy = _("This data needs administrator access.")
            else:  # UNSUPPORTED_HARDWARE
                reason = _("This hardware does not expose this data.")
                remedy = _("Nothing to do — the panel is not applicable to this machine.")
            self.show_unavailable(reason, remedy)
        elif isinstance(exc, ProviderTimeout | ProviderParseError):
            self.show_error(str(exc))
        else:
            log.exception("unexpected error in page load", exc_info=exc)
            self.show_error(_("Unexpected error: %s") % exc)
