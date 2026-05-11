## Copyright (C) 2026  Solaar Contributors https://pwr-solaar.github.io/Solaar/
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with this program; if not, write to the Free Software Foundation, Inc.,
## 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""Palette: active-color picker + a small gradient swatch widget.

The picker (`Palette`) is just a wrapped `Gtk.ColorButton` that emits
`color-changed` and remembers the previous active color. The previous
color is surfaced visually by the gradient tool button, not in the palette
itself — see `GradientSwatch` below, used by `editor.py`.
"""

from __future__ import annotations

from enum import Enum

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk  # NOQA: E402
from gi.repository import GObject  # NOQA: E402
from gi.repository import Gtk  # NOQA: E402

from solaar.i18n import _  # NOQA: E402

from ._icons import attach_themed_icon  # NOQA: E402

_UNSET_ICON_NAME = "solaar-tool-palette-off-symbolic"


class GtkSignal(Enum):
    DRAW = "draw"
    COLOR_SET = "color-set"
    TOGGLED = "toggled"


def _rgb_to_int(rgba: Gdk.RGBA) -> int:
    r = max(0, min(255, int(round(rgba.red * 255))))
    g = max(0, min(255, int(round(rgba.green * 255))))
    b = max(0, min(255, int(round(rgba.blue * 255))))
    return (r << 16) | (g << 8) | b


def _int_to_rgba(c: int) -> Gdk.RGBA:
    rgba = Gdk.RGBA()
    if c is None or c < 0:
        rgba.red = rgba.green = rgba.blue = 0.5
        rgba.alpha = 1.0
        return rgba
    rgba.red = ((c >> 16) & 0xFF) / 255.0
    rgba.green = ((c >> 8) & 0xFF) / 255.0
    rgba.blue = (c & 0xFF) / 255.0
    rgba.alpha = 1.0
    return rgba


# Sentinel for "no change" / unset paint. Matches special_keys.COLORSPLUS["No change"].
UNSET_COLOR = -1


class Palette(Gtk.Box):
    __gsignals__ = {
        "color-changed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __init__(self, active: int = 0xFF0000, previous: int = 0xFF0000) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        # _color/_last_color are always real RGB values; the unset toggle is
        # a separate channel so the gradient swatch (which mirrors these) is
        # unaffected by switching to "no change" paint mode.
        self._color: int = int(active)
        self._last_color: int = int(previous)
        self._unset_mode: bool = False

        self._color_btn = Gtk.ColorButton()
        self._color_btn.set_use_alpha(False)
        self._color_btn.set_rgba(_int_to_rgba(self._color))
        self._color_btn.set_tooltip_text(_("Active color"))
        self._color_btn.connect(GtkSignal.COLOR_SET.value, self._on_color_set)
        self.pack_start(self._color_btn, False, False, 0)

        self._unset_btn = Gtk.ToggleButton()
        self._unset_btn.set_tooltip_text(_("Paint as 'no change' — clears the cell to the zone base color"))
        unset_label = _("Unset")
        if attach_themed_icon(self._unset_btn, _UNSET_ICON_NAME) is not None:
            self._unset_btn.get_accessible().set_name(unset_label)
        else:
            self._unset_btn.set_label(unset_label)
        self._unset_btn.connect(GtkSignal.TOGGLED.value, self._on_unset_toggled)
        self.pack_start(self._unset_btn, False, False, 0)

    def shutdown(self) -> None:
        # attach_themed_icon connects to the button's own style-updated
        # signal; GTK disconnects it automatically when the button is
        # destroyed, so there is nothing to clean up here.
        pass

    def _on_color_set(self, btn: Gtk.ColorButton) -> None:
        c = _rgb_to_int(btn.get_rgba())
        unset_was_on = self._unset_mode
        if c == self._color and not unset_was_on:
            return
        if c != self._color:
            self._last_color = self._color
            self._color = c
        if unset_was_on:
            self._unset_mode = False
            self._unset_btn.set_active(False)
        self.emit("color-changed", self.get_color())

    def _on_unset_toggled(self, btn: Gtk.ToggleButton) -> None:
        new_state = bool(btn.get_active())
        if new_state == self._unset_mode:
            return
        self._unset_mode = new_state
        self.emit("color-changed", self.get_color())

    def get_color(self) -> int:
        return UNSET_COLOR if self._unset_mode else self._color

    def get_picker_color(self) -> int:
        """The most recent real RGB pick — independent of the unset toggle.
        Use this for visuals that should always reflect actual colors (e.g.
        the gradient swatch).
        """
        return self._color

    def get_last_color(self) -> int:
        return self._last_color

    def is_unset(self) -> bool:
        return self._unset_mode


class GradientSwatch(Gtk.DrawingArea):
    """Small icon: diagonal gradient from `previous` (bottom-left) to `active` (top-right).

    Used as the visual on the gradient tool button so the user can see at a
    glance which two colors the next gradient stroke will fade between.
    """

    SIZE = 22

    def __init__(self) -> None:
        super().__init__()
        self.set_size_request(self.SIZE, self.SIZE)
        self._active: int = 0xFF0000
        self._previous: int = 0xFF0000
        self.connect(GtkSignal.DRAW.value, self._on_draw)

    def update(self, active: int, previous: int) -> None:
        self._active = int(active)
        self._previous = int(previous)
        self.queue_draw()

    def get_active(self) -> int:
        return self._active

    def get_previous(self) -> int:
        return self._previous

    def get_colors(self) -> tuple[int, int]:
        """Return (active, previous) — the colors the gradient tool will paint with."""
        return (self._active, self._previous)

    def _on_draw(self, _w, cr) -> None:
        import cairo  # local: keeps the module light when GradientSwatch isn't built

        s = self.SIZE

        def rgb(c: int) -> tuple[float, float, float]:
            if c is None or c < 0:
                return (0.5, 0.5, 0.5)
            return (((c >> 16) & 0xFF) / 255.0, ((c >> 8) & 0xFF) / 255.0, (c & 0xFF) / 255.0)

        # Top-left (previous, gradient start) → bottom-right (active, end).
        # Matches the directional behavior of dragging the line tool TL → BR.
        pat = cairo.LinearGradient(0, 0, s, s)
        pat.add_color_stop_rgb(0.0, *rgb(self._previous))
        pat.add_color_stop_rgb(1.0, *rgb(self._active))
        cr.set_source(pat)
        cr.rectangle(0, 0, s, s)
        cr.fill()

        # Subtle border so the swatch reads as a control even on similar bg.
        cr.set_source_rgba(0, 0, 0, 0.45)
        cr.set_line_width(1.0)
        cr.rectangle(0.5, 0.5, s - 1, s - 1)
        cr.stroke()
