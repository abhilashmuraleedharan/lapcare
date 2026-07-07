# SPDX-License-Identifier: GPL-3.0-or-later
"""Main application window.

M0 Commit 10 state: an empty Adw.ApplicationWindow with a header bar and a
status page. The navigation shell (sidebar + pages) arrives in Commit 12,
which also introduces Blueprint layouts and `_()` string wrapping.
"""

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw

log = logging.getLogger(__name__)


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Lapcare")
        self.set_default_size(980, 640)

        status = Adw.StatusPage(
            title="Lapcare",
            description="Development skeleton (milestone M0)",
            icon_name="computer-symbolic",
        )
        toolbar_view = Adw.ToolbarView(content=status)
        toolbar_view.add_top_bar(Adw.HeaderBar())
        self.set_content(toolbar_view)
        log.debug("main window constructed")
