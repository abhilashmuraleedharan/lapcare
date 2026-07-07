# SPDX-License-Identifier: GPL-3.0-or-later
"""Reference view-model: the shape every page view-model copies.

A plain GObject exposing a `state` property (one of STATES) plus per-state
detail properties. Views bind to these; view-models never construct widgets.
Real pages (M1+) receive port implementations and the platform scheduler from
the composition root and populate state from async provider calls; the
reference page has no data source, so its transitions are driven by the debug
switcher (and the smoke test).

Testable without a display: GObject properties and signals need no GTK.
"""

from __future__ import annotations

import logging
from gettext import gettext as _

from gi.repository import GObject

log = logging.getLogger(__name__)

STATES = ("loading", "ready", "unavailable", "error")


class PlaceholderViewModel(GObject.Object):
    __gtype_name__ = "LapcarePlaceholderViewModel"

    state = GObject.Property(type=str, default="loading")
    unavailable_reason = GObject.Property(type=str, default="")
    unavailable_remedy = GObject.Property(type=str, default="")
    error_detail = GObject.Property(type=str, default="")

    def show_loading(self) -> None:
        self.props.state = "loading"

    def show_ready(self) -> None:
        self.props.state = "ready"

    def show_unavailable(self, reason: str, remedy: str) -> None:
        # Unavailable states always name the remedy (STYLEGUIDE): tell the
        # user what to install/enable, never a bare "no data".
        self.props.unavailable_reason = reason
        self.props.unavailable_remedy = remedy
        self.props.state = "unavailable"

    def show_error(self, detail: str) -> None:
        self.props.error_detail = detail
        self.props.state = "error"

    def demo_unavailable(self) -> None:
        """Debug-switcher example of a well-formed unavailable state."""
        self.show_unavailable(
            _("This panel needs a tool that is not installed."),
            _("Install the 'example-tool' package to enable it."),
        )

    def demo_error(self) -> None:
        """Debug-switcher example of a well-formed error state."""
        self.show_error(_("Example failure detail — copy this text into a bug report."))

    def advance(self) -> str:
        """Cycle to the next state (used by the smoke test). Returns it."""
        current = STATES.index(self.props.state)
        nxt = STATES[(current + 1) % len(STATES)]
        if nxt == "unavailable":
            self.demo_unavailable()
        elif nxt == "error":
            self.demo_error()
        else:
            self.props.state = nxt
        log.debug("state advanced to %s", nxt)
        return nxt
