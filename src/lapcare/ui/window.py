# SPDX-License-Identifier: GPL-3.0-or-later
"""Main application window: NavigationSplitView shell.

Pages arrive wired from the composition root as (id, title, widget); the
window never builds providers or view-models for real pages itself.

LAPCARE_SMOKE=1 makes the window visit every sidebar page on a timer (used
by the xvfb smoke test to render each page at least once).
"""

import logging
import os
from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from lapcare.ui.pages.placeholder.view import PlaceholderPage
from lapcare.ui.pages.placeholder.view_model import PlaceholderViewModel

log = logging.getLogger(__name__)

RESOURCE = "/io/github/abhilashmuraleedharan/lapcare/ui/window.ui"


@Gtk.Template(resource_path=RESOURCE)
class MainWindow(Adw.ApplicationWindow):
    __gtype_name__ = "LapcareMainWindow"

    split_view = Gtk.Template.Child()
    sidebar_list = Gtk.Template.Child()
    content_page = Gtk.Template.Child()
    page_container = Gtk.Template.Child()

    def __init__(self, pages=None, **kwargs):
        """``pages``: list of (page_id, title, widget) wired by the
        composition root. Falls back to the self-contained reference page."""
        super().__init__(**kwargs)

        self._pages: dict[str, tuple[str, object]] = {}
        self._current_page_id: str | None = None
        if pages is None:
            pages = [("reference", _("Reference"), PlaceholderPage(PlaceholderViewModel()))]
        for page_id, title, widget in pages:
            self._register_page(page_id, title, widget)

        self.sidebar_list.connect("row-selected", self._on_row_selected)
        self.sidebar_list.select_row(self.sidebar_list.get_row_at_index(0))
        log.debug("main window constructed with %d page(s)", len(self._pages))

        if os.environ.get("LAPCARE_SMOKE") == "1":
            self._smoke_index = 0
            GLib.timeout_add(300, self._smoke_visit_next)

    def _smoke_visit_next(self) -> bool:
        self._smoke_index += 1
        row = self.sidebar_list.get_row_at_index(self._smoke_index)
        if row is None:
            log.info("smoke: visited all pages")
            return False  # GLib.SOURCE_REMOVE
        self.sidebar_list.select_row(row)
        return True

    def _register_page(self, page_id: str, title: str, widget) -> None:
        row = Adw.ActionRow(title=title, activatable=True)
        row.page_id = page_id
        self.sidebar_list.append(row)
        self._pages[page_id] = (title, widget)

    def _on_row_selected(self, _listbox, row) -> None:
        if row is None or row.page_id == self._current_page_id:
            # Re-selecting the current row must not re-parent its widget:
            # adw_bin_set_child asserts the child has no parent.
            return
        self._current_page_id = row.page_id
        title, widget = self._pages[row.page_id]
        self.content_page.set_title(title)
        self.page_container.set_child(widget)
        self.split_view.set_show_content(True)
        log.debug("navigated to page=%s", row.page_id)
