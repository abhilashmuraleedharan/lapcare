# SPDX-License-Identifier: GPL-3.0-or-later
"""WearChart: a minimal wear-over-time line chart.

Custom-widget justification (STYLEGUIDE): GTK/libadwaita ship no charting
widget. Deliberately tiny — a theme-following line + fill over daily wear
percentages, y-scaled from 0 to a sensible headroom, with start/end day
labels. Anything fancier (axes, tooltips, zoom) waits for a real need.

Accessibility (ROADMAP M5): the widget reports role IMG with a label that
summarizes the series (a screen reader hears the data, not silence), and the
day labels are laid out with Pango using the widget's own font context, so
system font scaling applies to them like any other text.
"""

from __future__ import annotations

import logging
from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango, PangoCairo

log = logging.getLogger(__name__)

_PAD = 8.0


class WearChart(Gtk.DrawingArea):
    __gtype_name__ = "LapcareWearChart"

    def __init__(self, **kwargs):
        super().__init__(accessible_role=Gtk.AccessibleRole.IMG, **kwargs)
        self._points: list[tuple[str, float]] = []
        self.set_content_height(110)
        self.set_hexpand(True)
        self.set_draw_func(self._draw)

    def set_points(self, points: list[tuple[str, float]]) -> None:
        """(ISO day, wear %) samples, ascending by day."""
        self._points = points
        if points:
            first_day, first_wear = points[0]
            last_day, last_wear = points[-1]
            self.update_property(
                [Gtk.AccessibleProperty.LABEL],
                [
                    _(
                        "Wear history chart: %(count)d daily samples, "
                        "%(first).1f%% wear on %(first_day)s to "
                        "%(last).1f%% wear on %(last_day)s"
                    )
                    % {
                        "count": len(points),
                        "first": first_wear,
                        "first_day": first_day,
                        "last": last_wear,
                        "last_day": last_day,
                    }
                ],
            )
        self.queue_draw()

    def _day_layout(self, text: str) -> Pango.Layout:
        # The widget's own Pango context: follows theme font + system font
        # scaling, unlike cairo "toy text" with a fixed pixel size.
        layout = self.create_pango_layout(text)
        font = self.get_pango_context().get_font_description()
        font.set_size(int(font.get_size() * 0.85))
        layout.set_font_description(font)
        return layout

    def _draw(self, _area, cr, width: int, height: int) -> None:
        if not self._points:
            return
        color = self.get_color()  # follows light/dark theme
        cr.set_source_rgba(color.red, color.green, color.blue, 0.9)

        first_layout = self._day_layout(self._points[0][0])
        last_layout = self._day_layout(self._points[-1][0])
        label_h = first_layout.get_pixel_size().height

        values = [wear for _day, wear in self._points]
        y_max = max(10.0, max(values) * 1.25)
        plot_w = width - 2 * _PAD
        plot_h = max(10.0, height - 2 * _PAD - label_h - 4.0)

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
        last_x, _y = xy(len(values) - 1, values[-1])
        first_x, _y = xy(0, values[0])
        cr.line_to(last_x, _PAD + plot_h)
        cr.line_to(first_x, _PAD + plot_h)
        cr.close_path()
        cr.set_source_rgba(color.red, color.green, color.blue, 0.15)
        cr.fill()

        # Start/end day labels.
        cr.set_source_rgba(color.red, color.green, color.blue, 0.6)
        label_y = height - _PAD / 2 - label_h
        cr.move_to(_PAD, label_y)
        PangoCairo.show_layout(cr, first_layout)
        cr.move_to(width - _PAD - last_layout.get_pixel_size().width, label_y)
        PangoCairo.show_layout(cr, last_layout)
