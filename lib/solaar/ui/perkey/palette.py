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
    CLICKED = "clicked"
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

    # Clickable preset swatches offered in the sidebar. A representative
    # spread of common key colours; custom colours can always be picked with
    # the color button above them.
    _PRESET_COLORS: tuple[int, ...] = (
        0xFF0000, 0xFF6600, 0xFFFF00, 0x00FF00, 0x00CCFF, 0x0000FF,
        0x9B30FF, 0xFF1493, 0xFFFFFF, 0xCCCCCC, 0x666666, 0x000000,
    )
    _SWATCH_SIZE = 24
    _PRESETS_PER_LINE = 4

    def __init__(
        self,
        active: int = 0xFF0000,
        previous: int = 0xFF0000,
        orientation: Gtk.Orientation = Gtk.Orientation.HORIZONTAL,
    ) -> None:
        super().__init__(orientation=orientation, spacing=8)
        # _color/_last_color are always real RGB values; the unset toggle is
        # a separate channel so the gradient swatch (which mirrors these) is
        # unaffected by switching to "no change" paint mode.
        self._color: int = int(active)
        self._last_color: int = int(previous)
        self._unset_mode: bool = False

        # Active colour swatch: opens the full GTK colour dialog, so any
        # custom colour can be picked and the current one modified.
        self._color_btn = Gtk.ColorButton()
        self._color_btn.set_use_alpha(False)
        self._color_btn.set_rgba(_int_to_rgba(self._color))
        self._color_btn.set_tooltip_text(_("Choose a colour"))
        self._color_btn.set_hexpand(True)
        self._color_btn.set_size_request(-1, 36)
        self._color_btn.connect(GtkSignal.COLOR_SET.value, self._on_color_set)
        self.pack_start(self._color_btn, False, False, 0)

        # Preset colours grid.
        self.pack_start(self._section_label(_("Presets")), False, False, 0)
        self._preset_flow = self._new_flow()
        for c in self._PRESET_COLORS:
            self._preset_flow.add(self._make_swatch(c))
        self.pack_start(self._preset_flow, False, False, 0)

        # Colours currently used on the keys — visible so any one can be
        # quickly reused (or re-picked in the colour dialog to modify it).
        self._used_label = self._section_label(_("Used colours"))
        self._used_flow = self._new_flow()
        self.pack_start(self._used_label, False, False, 0)
        self.pack_start(self._used_flow, False, False, 0)

        # "No change" toggle.
        self._unset_btn = Gtk.ToggleButton()
        self._unset_btn.set_tooltip_text(_("Paint as 'no change' — clears the cell to the zone base color"))
        unset_label = _("Unset")
        if attach_themed_icon(self._unset_btn, _UNSET_ICON_NAME) is not None:
            self._unset_btn.get_accessible().set_name(unset_label)
        else:
            self._unset_btn.set_label(unset_label)
        self._unset_btn.connect(GtkSignal.TOGGLED.value, self._on_unset_toggled)
        self.pack_start(self._unset_btn, False, False, 0)

    @staticmethod
    def _section_label(text: str) -> Gtk.Label:
        label = Gtk.Label(label=text)
        label.set_xalign(0.0)
        label.get_style_context().add_class("dim-label")
        return label

    @staticmethod
    def _new_flow() -> Gtk.FlowBox:
        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(Palette._PRESETS_PER_LINE)
        flow.set_min_children_per_line(Palette._PRESETS_PER_LINE)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(True)
        flow.set_row_spacing(4)
        flow.set_column_spacing(4)
        return flow

    def _make_swatch(self, color: int) -> Gtk.Button:
        btn = Gtk.Button()
        btn.add(GradientSwatch(size=self._SWATCH_SIZE, solid=color))
        btn.set_tooltip_text(_("#%06X") % color)
        btn.connect(GtkSignal.CLICKED.value, self._on_swatch_clicked, color)
        return btn

    def shutdown(self) -> None:
        # attach_themed_icon connects to the button's own style-updated
        # signal; GTK disconnects it automatically when the button is
        # destroyed, so there is nothing to clean up here.
        pass

    def _on_swatch_clicked(self, _btn, color: int) -> None:
        if color == self._color and not self._unset_mode:
            return
        self._last_color = self._color
        self._color = int(color)
        self._unset_mode = False
        self._unset_btn.set_active(False)
        self._color_btn.set_rgba(_int_to_rgba(self._color))
        self.emit("color-changed", self._color)

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

    def set_used_colors(self, colors) -> None:
        """Rebuild the 'used colours' row from the colours currently on the keys."""
        # De-duplicate while preserving first-seen order.
        seen = set()
        ordered = []
        for c in colors:
            try:
                c = int(c)
            except (TypeError, ValueError):
                continue
            if c < 0 or c in seen:
                continue
            seen.add(c)
            ordered.append(c)
        for child in list(self._used_flow.get_children()):
            self._used_flow.remove(child)
        for c in ordered:
            self._used_flow.add(self._make_swatch(c))
        self._used_label.set_visible(bool(ordered))
        self._used_flow.set_visible(bool(ordered))
        self._used_flow.show_all()

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
    """Colour swatch drawn with cairo.

    In gradient mode (default) it shows a diagonal gradient from `previous`
    (bottom-left) to `active` (top-right), used as the visual on the gradient
    tool button. With `solid` supplied it renders that single colour and is
    used as a clickable preset / used-colour swatch in the sidebar.
    """

    SIZE = 22

    def __init__(self, size: int = SIZE, solid: int | None = None) -> None:
        super().__init__()
        self._size = int(size)
        self.set_size_request(self._size, self._size)
        self._active: int = 0xFF0000
        self._previous: int = 0xFF0000
        self._solid: int | None = solid
        self.connect(GtkSignal.DRAW.value, self._on_draw)
        # Re-render when the GTK theme changes, so the rounded-square
        # outline (drawn in the theme foreground color) stays in sync
        # with the tool icons next to it.
        self.connect("style-updated", lambda w: w.queue_draw())

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

    @staticmethod
    def _rounded_rect_path(cr, x: float, y: float, w: float, h: float, r: float) -> None:
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -1.5708, 0)
        cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
        cr.arc(x + r, y + h - r, r, 1.5708, 3.1416)
        cr.arc(x + r, y + r, r, 3.1416, 4.7124)
        cr.close_path()

    def _on_draw(self, _w, cr) -> None:
        import cairo  # local: keeps the module light when GradientSwatch isn't built

        def rgb(c: int) -> tuple[float, float, float]:
            if c is None or c < 0:
                return (0.5, 0.5, 0.5)
            return (((c >> 16) & 0xFF) / 255.0, ((c >> 8) & 0xFF) / 255.0, (c & 0xFF) / 255.0)

        # Render in Tabler "square" coordinates (24x24 viewBox, rounded
        # rect from (3,3) to (21,21), corner radius 2, stroke 2) and let
        # cairo scale to the swatch's pixel size. Matches the outline
        # style of the tool icons exactly.
        cr.save()
        cr.scale(self._size / 24.0, self._size / 24.0)

        # Build the rounded-square path once, clip+fill the colour
        # (solid or gradient) inside it, then re-build and stroke the
        # outline in the theme foreground color.
        self._rounded_rect_path(cr, 3, 3, 18, 18, 2)
        cr.save()
        cr.clip()
        if self._solid is not None:
            r, g, b = rgb(self._solid)
            cr.set_source_rgba(r, g, b, 1.0)
            cr.rectangle(3, 3, 18, 18)
            cr.fill()
        else:
            # Top-left (previous, gradient start) → bottom-right (active, end).
            # Matches the directional behavior of dragging the line tool TL → BR.
            # Endpoints are shifted inward by the arc inset (corner radius * (1
            # - 1/sqrt(2)), ~0.586 for r=2) so t=0 lands on the actual visible
            # TL corner pixel of the rounded rect — without this, the rendered
            # corners sample at t≈0.033/0.967 and the displayed colors are
            # ~8 RGB units short of the true endpoint colors.
            inset = 2 * (1 - 1 / (2**0.5))
            pat = cairo.LinearGradient(3 + inset, 3 + inset, 21 - inset, 21 - inset)
            pat.add_color_stop_rgb(0.0, *rgb(self._previous))
            pat.add_color_stop_rgb(1.0, *rgb(self._active))
            cr.set_source(pat)
            cr.rectangle(3, 3, 18, 18)
            cr.fill()
        cr.restore()  # drop clip

        self._rounded_rect_path(cr, 3, 3, 18, 18, 2)
        fg = self.get_style_context().get_color(Gtk.StateFlags.NORMAL)
        cr.set_source_rgba(fg.red, fg.green, fg.blue, fg.alpha)
        cr.set_line_width(2)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.stroke()
        cr.restore()
