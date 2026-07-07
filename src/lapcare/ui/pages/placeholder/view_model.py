# SPDX-License-Identifier: GPL-3.0-or-later
"""Reference view-model: the shape every page view-model copies.

Extends PageViewModel (the four-state contract) with debug-switcher content.
Real pages add data properties and async loading via the scheduler — see
ui/pages/dashboard/view_model.py for the live example.
"""

from __future__ import annotations

import logging
from gettext import gettext as _

from lapcare.ui.pages.base_view_model import STATES, PageViewModel

__all__ = ["STATES", "PlaceholderViewModel"]

log = logging.getLogger(__name__)


class PlaceholderViewModel(PageViewModel):
    __gtype_name__ = "LapcarePlaceholderViewModel"

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
