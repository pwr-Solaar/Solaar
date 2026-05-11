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

"""Cairo-rendered keyboard canvas. Renders a BoundLayout as colored rectangles
and dispatches paint events through a configurable Tool to the editor.
"""

from __future__ import annotations

import logging

from enum import Enum
from typing import Callable

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk  # NOQA: E402
from gi.repository import GObject  # NOQA: E402
from gi.repository import Gtk  # NOQA: E402

from .layout import BoundCell  # NOQA: E402
from .layout import BoundLayout  # NOQA: E402
from .tools import TOOLS  # NOQA: E402
from .tools import ToolContext  # NOQA: E402

logger = logging.getLogger(__name__)


class GtkSignal(Enum):
    DRAW = "draw"
    BUTTON_PRESS_EVENT = "button-press-event"
    BUTTON_RELEASE_EVENT = "button-release-event"
    MOTION_NOTIFY_EVENT = "motion-notify-event"
    LEAVE_NOTIFY_EVENT = "leave-notify-event"


CELL_PX = 36
GUTTER_PX = 4
STRIP_GAP_PX = 16
PADDING_PX = 8


class KeyboardCanvas(Gtk.DrawingArea):
    __gsignals__ = {
        # Emitted on stroke release. delta is dict[zone_id, color].
        "paint": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self) -> None:
        super().__init__()
        self._bound: BoundLayout | None = None
        self._colors: dict[int, int] = {}  # zone_id -> packed RGB or -1 (unset)
        self._active_color: int = 0xFF0000
        self._gradient_colors_source: Callable[[], tuple[int, int]] | None = None
        self._zone_base_color: int | None = None
        self._tool_name: str = "single"
        self._press_cell: BoundCell | None = None
        self._motion_cell: BoundCell | None = None
        self._brush_path: list[int] = []
        self._dragging: bool = False
        self.set_can_focus(True)
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        self.connect(GtkSignal.DRAW.value, self._on_draw)
        self.connect(GtkSignal.BUTTON_PRESS_EVENT.value, self._on_press)
        self.connect(GtkSignal.BUTTON_RELEASE_EVENT.value, self._on_release)
        self.connect(GtkSignal.MOTION_NOTIFY_EVENT.value, self._on_motion)
        self.connect(GtkSignal.LEAVE_NOTIFY_EVENT.value, self._on_leave)

    # ---- public API ----

    def set_layout(self, bound: BoundLayout) -> None:
        self._bound = bound
        self._update_size()
        self.queue_draw()

    def set_colors(self, colors: dict[int, int]) -> None:
        self._colors = dict(colors)
        self.queue_draw()

    def update_colors(self, deltas: dict[int, int]) -> None:
        self._colors.update(deltas)
        self.queue_draw()

    def set_active_color(self, color: int) -> None:
        self._active_color = int(color)

    def set_gradient_colors_source(self, source: Callable[[], tuple[int, int]] | None) -> None:
        self._gradient_colors_source = source

    def set_zone_base_color(self, color: int | None) -> None:
        self._zone_base_color = None if color is None else int(color)
        self.queue_draw()

    def set_tool(self, name: str) -> None:
        if name in TOOLS:
            self._tool_name = name

    # ---- size / hit-test ----

    def _matrix_size(self) -> tuple[int, int]:
        if not self._bound:
            return 0, 0
        max_col = 0
        max_row = 0
        for bc in self._bound.matrix:
            c = bc.cell
            max_col = max(max_col, c.col + int(round(c.width)))
            max_row = max(max_row, c.row + int(round(c.height)))
        return max_row, max_col

    def _strip_size(self) -> int:
        if not self._bound:
            return 0
        return len(self._bound.strip)

    def _update_size(self) -> None:
        rows, cols = self._matrix_size()
        strip_n = self._strip_size()
        w = PADDING_PX * 2 + cols * CELL_PX + max(0, cols - 1) * GUTTER_PX
        matrix_h = rows * CELL_PX + max(0, rows - 1) * GUTTER_PX
        strip_h = (CELL_PX + STRIP_GAP_PX) if strip_n else 0
        h = PADDING_PX * 2 + matrix_h + strip_h
        # widen if strip is wider than matrix
        if strip_n:
            sw = PADDING_PX * 2 + strip_n * CELL_PX + max(0, strip_n - 1) * GUTTER_PX
            w = max(w, sw)
        self.set_size_request(w, h)

    def _cell_rect(self, bc: BoundCell) -> tuple[float, float, float, float]:
        c = bc.cell
        if self._bound is not None and bc in self._bound.strip:
            # strip cells: laid out in a flat row beneath the matrix
            rows, _cols = self._matrix_size()
            matrix_h = rows * CELL_PX + max(0, rows - 1) * GUTTER_PX
            strip_idx = self._bound.strip.index(bc)
            x = PADDING_PX + strip_idx * (CELL_PX + GUTTER_PX)
            y = PADDING_PX + matrix_h + STRIP_GAP_PX
            return (x, y, CELL_PX, CELL_PX)
        x = PADDING_PX + c.col * (CELL_PX + GUTTER_PX)
        y = PADDING_PX + c.row * (CELL_PX + GUTTER_PX)
        w = c.width * CELL_PX + max(0.0, c.width - 1.0) * GUTTER_PX
        h = c.height * CELL_PX + max(0.0, c.height - 1.0) * GUTTER_PX
        return (x, y, w, h)

    def _cell_at(self, x: float, y: float) -> BoundCell | None:
        if not self._bound:
            return None
        for bc in list(self._bound.matrix) + list(self._bound.strip):
            cx, cy, cw, ch = self._cell_rect(bc)
            if cx <= x < cx + cw and cy <= y < cy + ch:
                return bc
        return None

    # ---- draw ----

    def _on_draw(self, _widget, cr) -> bool:
        if not self._bound:
            return False
        for bc in self._bound.matrix:
            self._draw_cell(cr, bc)
        for bc in self._bound.strip:
            self._draw_cell(cr, bc)
        if self._dragging and self._press_cell and self._motion_cell:
            tool = TOOLS.get(self._tool_name)
            if tool is not None:
                if tool.overlay_shape == "rect":
                    self._draw_rect_overlay(cr, self._press_cell, self._motion_cell)
                elif tool.overlay_shape == "line":
                    self._draw_line_overlay(cr, self._press_cell, self._motion_cell)
        return False

    def _draw_cell(self, cr, bc: BoundCell) -> None:
        x, y, w, h = self._cell_rect(bc)
        color = self._colors.get(bc.cell.zone_id, -1)
        # background
        if not bc.bound:
            cr.set_source_rgba(0.18, 0.18, 0.20, 1.0)
        elif color is None or color < 0:
            self._fill_checker(cr, x, y, w, h)
            cr.set_source_rgba(0, 0, 0, 0)  # no overlay fill
        else:
            r = ((color >> 16) & 0xFF) / 255.0
            g = ((color >> 8) & 0xFF) / 255.0
            b = (color & 0xFF) / 255.0
            cr.set_source_rgba(r, g, b, 1.0)
        if bc.bound and (color is not None and color >= 0):
            self._round_rect(cr, x, y, w, h, 4)
            cr.fill_preserve()
        elif not bc.bound:
            self._round_rect(cr, x, y, w, h, 4)
            cr.fill_preserve()
        else:
            self._round_rect(cr, x, y, w, h, 4)
        # border
        cr.set_source_rgba(0, 0, 0, 0.55)
        cr.set_line_width(1.0)
        cr.stroke()
        # label
        label = bc.cell.label or str(bc.cell.zone_id)
        cr.set_source_rgba(*self._label_color(color, bc.bound))
        cr.select_font_face("Sans")
        cr.set_font_size(11.0 if len(label) <= 3 else 9.0)
        try:
            extents = cr.text_extents(label)
            tx = x + (w - extents.width) / 2 - extents.x_bearing
            ty = y + (h + extents.height) / 2 - extents.y_bearing - extents.height
            cr.move_to(tx, ty)
            cr.show_text(label)
        except Exception as e:
            logger.debug("text rendering failed for %r: %s", label, e)

    def _fill_checker(self, cr, x, y, w, h) -> None:
        # Diagonal hash for "no change" cells. Background uses the zone base
        # color (what these cells actually display on the keyboard); stripes
        # pick a black or white contrast based on luminance.
        cr.save()
        self._round_rect(cr, x, y, w, h, 4)
        cr.clip()
        base = self._zone_base_color
        if base is not None and base >= 0:
            r = ((base >> 16) & 0xFF) / 255.0
            g = ((base >> 8) & 0xFF) / 255.0
            b = (base & 0xFF) / 255.0
        else:
            r = g = 0.30
            b = 0.32
        cr.set_source_rgba(r, g, b, 1.0)
        cr.rectangle(x, y, w, h)
        cr.fill()
        if base is not None and base >= 0:
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            cr.set_source_rgba(0, 0, 0, 0.45) if lum > 0.55 else cr.set_source_rgba(1, 1, 1, 0.35)
        else:
            cr.set_source_rgba(0.55, 0.55, 0.60, 1.0)
        cr.set_line_width(1.5)
        step = 5
        d_max = int(w + h)
        d = -int(h)
        while d <= d_max:
            cr.move_to(x + d, y + h)
            cr.line_to(x + d + h, y)
            cr.stroke()
            d += step
        cr.restore()

    def _round_rect(self, cr, x, y, w, h, r) -> None:
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -1.5708, 0)
        cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
        cr.arc(x + r, y + h - r, r, 1.5708, 3.1416)
        cr.arc(x + r, y + r, r, 3.1416, 4.7124)
        cr.close_path()

    def _label_color(self, color: int, bound: bool) -> tuple[float, float, float, float]:
        if not bound:
            return (0.50, 0.50, 0.52, 1.0)
        if color is None or color < 0:
            return (0.85, 0.85, 0.88, 1.0)
        # luminance heuristic
        r = ((color >> 16) & 0xFF) / 255.0
        g = ((color >> 8) & 0xFF) / 255.0
        b = (color & 0xFF) / 255.0
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        return (0, 0, 0, 1.0) if lum > 0.55 else (1, 1, 1, 1.0)

    def _draw_rect_overlay(self, cr, a: BoundCell, b: BoundCell) -> None:
        ax, ay, aw, ah = self._cell_rect(a)
        bx, by, bw, bh = self._cell_rect(b)
        x0 = min(ax, bx) - 2
        y0 = min(ay, by) - 2
        x1 = max(ax + aw, bx + bw) + 2
        y1 = max(ay + ah, by + bh) + 2
        cr.set_source_rgba(0.30, 0.65, 1.0, 0.85)
        cr.set_line_width(1.5)
        cr.set_dash([4.0, 3.0])
        cr.rectangle(x0, y0, x1 - x0, y1 - y0)
        cr.stroke()
        cr.set_dash([])

    def _draw_line_overlay(self, cr, a: BoundCell, b: BoundCell) -> None:
        ax, ay, aw, ah = self._cell_rect(a)
        bx, by, bw, bh = self._cell_rect(b)
        ax_c, ay_c = ax + aw / 2, ay + ah / 2
        bx_c, by_c = bx + bw / 2, by + bh / 2
        cr.set_source_rgba(0.30, 0.65, 1.0, 0.95)
        cr.set_line_width(2.0)
        cr.set_dash([5.0, 3.0])
        cr.move_to(ax_c, ay_c)
        cr.line_to(bx_c, by_c)
        cr.stroke()
        cr.set_dash([])
        # endpoint dots — solid so the anchors read clearly
        for cx, cy in ((ax_c, ay_c), (bx_c, by_c)):
            cr.arc(cx, cy, 4.0, 0, 6.283)
            cr.fill()

    # ---- input ----

    def _on_press(self, _w, event: Gdk.EventButton) -> bool:
        if event.button != 1:
            return False
        bc = self._cell_at(event.x, event.y)
        if bc is None or not bc.bound:
            return False
        self._press_cell = bc
        self._motion_cell = bc
        self._dragging = True
        self._brush_path = [bc.cell.zone_id]
        tool = TOOLS.get(self._tool_name)
        if tool is not None and tool.is_brush:
            self.update_colors({bc.cell.zone_id: self._active_color})
        else:
            self.queue_draw()
        return True

    def _on_motion(self, _w, event: Gdk.EventMotion) -> bool:
        if not self._dragging:
            return False
        bc = self._cell_at(event.x, event.y)
        if bc is None or not bc.bound:
            return False
        if bc is self._motion_cell:
            return False
        self._motion_cell = bc
        tool = TOOLS.get(self._tool_name)
        if tool is not None and tool.is_brush:
            if bc.cell.zone_id not in self._brush_path:
                self._brush_path.append(bc.cell.zone_id)
                self.update_colors({bc.cell.zone_id: self._active_color})
        else:
            self.queue_draw()
        return True

    def _on_release(self, _w, event: Gdk.EventButton) -> bool:
        if event.button != 1 or not self._dragging:
            return False
        self._dragging = False
        if self._press_cell is None:
            return False
        if self._bound:
            bound_zones = {bc.cell.zone_id: bc for bc in list(self._bound.matrix) + list(self._bound.strip)}
            strip_zones = frozenset(bc.cell.zone_id for bc in self._bound.strip)
        else:
            bound_zones = {}
            strip_zones = frozenset()
        if self._tool_name == "gradient" and self._gradient_colors_source is not None:
            grad_active, grad_previous = self._gradient_colors_source()
            ctx = ToolContext(
                active_color=int(grad_active),
                last_color=int(grad_previous),
                cells_by_zone=bound_zones,
                strip_zones=strip_zones,
                current_colors=dict(self._colors),
            )
        else:
            ctx = ToolContext(
                active_color=self._active_color,
                last_color=self._active_color,
                cells_by_zone=bound_zones,
                strip_zones=strip_zones,
                current_colors=dict(self._colors),
            )
        tool = TOOLS.get(self._tool_name)
        delta: dict[int, int] = {}
        if tool is not None:
            delta = tool.compute(self._press_cell, self._motion_cell, list(self._brush_path), ctx)
        self._press_cell = None
        self._motion_cell = None
        self._brush_path = []
        self.queue_draw()
        if delta:
            self.update_colors(delta)
            self.emit("paint", delta)
        return True

    def _on_leave(self, _w, _event) -> bool:
        # don't cancel drags on leave; let the user re-enter
        return False
