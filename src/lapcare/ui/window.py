# SPDX-License-Identifier: GPL-3.0-or-later
"""Main application window: NavigationSplitView shell.

Sidebar rows and their pages are registered in __init__; M1 replaces the
reference page with real pages (Dashboard, Hardware, …), each constructed
with its view-model by the composition root and handed in — the window never
builds providers or view-models for real pages itself.
"""

import logging
from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # M0: the reference page is self-contained (no ports), so the window
        # may construct it. Real pages arrive wired from app.py.
        self._pages: dict[str, tuple[str, object]] = {}
        self._current_page_id: str | None = None
        self._register_page("reference", _("Reference"), PlaceholderPage(PlaceholderViewModel()))

        self.sidebar_list.connect("row-selected", self._on_row_selected)
        self.sidebar_list.select_row(self.sidebar_list.get_row_at_index(0))
        log.debug("main window constructed with %d page(s)", len(self._pages))

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
