# SPDX-License-Identifier: GPL-3.0-or-later
"""WearChart: a minimal wear-over-time line chart.

Custom-widget justification (STYLEGUIDE): GTK/libadwaita ship no charting
widget. Deliberately tiny — a theme-following line + fill over daily wear
percentages, y-scaled from 0 to a sensible headroom, with start/end day
labels. Anything fancier (axes, tooltips, zoom) waits for a real need.
"""

from __future__ import annotations

import logging

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

log = logging.getLogger(__name__)

_PAD = 8.0
_LABEL_SPACE = 16.0


class WearChart(Gtk.DrawingArea):
    __gtype_name__ = "LapcareWearChart"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._points: list[tuple[str, float]] = []
        self.set_content_height(110)
        self.set_hexpand(True)
        self.set_draw_func(self._draw)

    def set_points(self, points: list[tuple[str, float]]) -> None:
        """(ISO day, wear %) samples, ascending by day."""
        self._points = points
        self.queue_draw()

    def _draw(self, _area, cr, width: int, height: int) -> None:
        if not self._points:
            return
        color = self.get_color()  # follows light/dark theme
        cr.set_source_rgba(color.red, color.green, color.blue, 0.9)

        values = [wear for _day, wear in self._points]
        y_max = max(10.0, max(values) * 1.25)
        plot_w = width - 2 * _PAD
        plot_h = height - 2 * _PAD - _LABEL_SPACE

        def xy(index: int, wear: float) -> tuple[float, float]:
            x_frac = index / (len(values) - 1) if len(values) > 1 else 0.5
            return (_PAD + x_frac * plot_w, _PAD + (1.0 - wear / y_max) * plot_h)

        cr.set_line_width(2.0)
        for i, value in enumerate(values):
            x, y = xy(i, value)
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        cr.stroke_preserve()

        # Soft fill under the line.
        last_x, _ = xy(len(values) - 1, values[-1])
        first_x, _ = xy(0, values[0])
        cr.line_to(last_x, _PAD + plot_h)
        cr.line_to(first_x, _PAD + plot_h)
        cr.close_path()
        cr.set_source_rgba(color.red, color.green, color.blue, 0.15)
        cr.fill()

        # Start/end day labels.
        cr.set_source_rgba(color.red, color.green, color.blue, 0.6)
        cr.set_font_size(10)
        cr.move_to(_PAD, height - _PAD / 2)
        cr.show_text(self._points[0][0])
        extents = cr.text_extents(self._points[-1][0])
        cr.move_to(width - _PAD - extents.width, height - _PAD / 2)
        cr.show_text(self._points[-1][0])
