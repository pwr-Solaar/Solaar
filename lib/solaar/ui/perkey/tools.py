## Copyright (C) 2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
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

"""Paint tools for the per-key editor.

Each tool is a stateless policy object. The Canvas owns per-stroke state
(press cell, motion cell, brush path) and asks the active tool for the
final delta on release.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from typing import Protocol

from .layout import BoundCell
from .layout import Cell


@dataclass
class ToolContext:
    active_color: int
    last_color: int
    cells_by_zone: dict[int, BoundCell]
    # zone ids that live in the bottom strip (e.g. logo, G-keys); kept separate
    # because their on-screen position is decoupled from the matrix grid.
    strip_zones: frozenset = frozenset()
    # zone_id -> current packed RGB (or -1 sentinel for unset). Used by tools
    # that need to compare colors, like the flood-fill bucket.
    current_colors: dict = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.current_colors is None:
            self.current_colors = {}

    def bound_cells(self) -> list[BoundCell]:
        return list(self.cells_by_zone.values())

    def matrix_cells(self) -> list[BoundCell]:
        cells = [bc for bc in self.cells_by_zone.values() if bc.bound and bc.cell.zone_id not in self.strip_zones]
        if cells:
            return cells
        # No matrix region (e.g. a mouse, where every zone lives in the
        # strip). Fall back to all bound cells so directional tools still
        # have something to project across.
        return [bc for bc in self.cells_by_zone.values() if bc.bound]

    def cells_in_bbox(self, a: BoundCell, b: BoundCell) -> list[BoundCell]:
        cx_a, cy_a = _cell_center(a.cell)
        cx_b, cy_b = _cell_center(b.cell)
        x0, x1 = (cx_a, cx_b) if cx_a <= cx_b else (cx_b, cx_a)
        y0, y1 = (cy_a, cy_b) if cy_a <= cy_b else (cy_b, cy_a)
        result = []
        for bc in self.cells_by_zone.values():
            if not bc.bound:
                continue
            cx, cy = _cell_center(bc.cell)
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                result.append(bc)
        return result

    def cells_in_bbox_ordered(self, a: BoundCell, b: BoundCell) -> list[BoundCell]:
        cells = self.cells_in_bbox(a, b)
        return sorted(cells, key=lambda c: (c.cell.row, c.cell.col))

    def cells_in_group(self, group: str) -> list[BoundCell]:
        return [bc for bc in self.cells_by_zone.values() if bc.bound and bc.cell.group == group]


def _cell_center(cell: Cell) -> tuple[float, float]:
    return (cell.col + cell.width / 2.0, cell.row + cell.height / 2.0)


def _cells_touch(a: Cell, b: Cell) -> bool:
    """Bounding-box edge adjacency in grid units. Handles variable widths
    (Space spans multiple cols, Numpad+ spans multiple rows).
    """
    a_c1, a_r1 = a.col + a.width, a.row + a.height
    b_c1, b_r1 = b.col + b.width, b.row + b.height
    rows_overlap = a.row < b_r1 and b.row < a_r1
    cols_overlap = a.col < b_c1 and b.col < a_c1
    if (a_c1 == b.col or b_c1 == a.col) and rows_overlap:
        return True
    if (a_r1 == b.row or b_r1 == a.row) and cols_overlap:
        return True
    return False


class Tool(Protocol):
    name: str
    is_brush: bool
    overlay_shape: str  # "" | "rect"

    def compute(
        self,
        start: BoundCell | None,
        end: BoundCell | None,
        path: Iterable[int],
        ctx: ToolContext,
    ) -> dict[int, int]:
        ...


class SingleTool:
    name = "single"
    is_brush = True
    overlay_shape = ""

    def compute(self, start, end, path, ctx):
        return {z: ctx.active_color for z in path}


class RectTool:
    name = "rect"
    is_brush = False
    overlay_shape = "rect"

    def compute(self, start, end, path, ctx):
        if start is None or end is None:
            return {}
        return {bc.cell.zone_id: ctx.active_color for bc in ctx.cells_in_bbox(start, end)}


class BucketTool:
    """Flood-fill: replace the clicked cell's color in every connected cell
    of the same color (4-adjacent on the matrix grid). Strip cells aren't on
    the matrix grid, so clicking one paints just that cell.
    """

    name = "bucket"
    is_brush = False
    overlay_shape = ""

    def compute(self, start, end, path, ctx):
        if start is None:
            return {}
        new_color = ctx.active_color
        target = ctx.current_colors.get(start.cell.zone_id, -1)
        if target == new_color:
            return {}
        if start.cell.zone_id in ctx.strip_zones:
            return {start.cell.zone_id: new_color}
        # BFS over matrix cells
        cells_by_id = {z: bc for z, bc in ctx.cells_by_zone.items() if bc.bound and z not in ctx.strip_zones}
        visited = {start.cell.zone_id}
        stack = [start]
        result: dict[int, int] = {}
        while stack:
            bc = stack.pop()
            result[bc.cell.zone_id] = new_color
            for other in cells_by_id.values():
                if other.cell.zone_id in visited:
                    continue
                if ctx.current_colors.get(other.cell.zone_id, -1) != target:
                    continue
                if not _cells_touch(bc.cell, other.cell):
                    continue
                visited.add(other.cell.zone_id)
                stack.append(other)
        return result


class GradientTool:
    """Directional gradient: drag a line from A to B, the whole matrix gets a
    gradient at that angle. Cells projecting before A clamp to the previous
    color; cells past B clamp to the active color.
    """

    name = "gradient"
    is_brush = False
    overlay_shape = "line"

    def compute(self, start, end, path, ctx):
        if start is None or end is None:
            return {}
        ax, ay = _cell_center(start.cell)
        bx, by = _cell_center(end.cell)
        vx, vy = bx - ax, by - ay
        length_sq = vx * vx + vy * vy
        if length_sq == 0:
            return {start.cell.zone_id: ctx.active_color}
        result: dict[int, int] = {}
        for bc in ctx.matrix_cells():
            cx, cy = _cell_center(bc.cell)
            t = ((cx - ax) * vx + (cy - ay) * vy) / length_sq
            t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
            result[bc.cell.zone_id] = _lerp_rgb(ctx.last_color, ctx.active_color, t)
        return result


def _lerp_rgb(c0: int, c1: int, t: float) -> int:
    if c0 < 0:
        c0 = c1
    if c1 < 0:
        c1 = c0
    r0, g0, b0 = (c0 >> 16) & 0xFF, (c0 >> 8) & 0xFF, c0 & 0xFF
    r1, g1, b1 = (c1 >> 16) & 0xFF, (c1 >> 8) & 0xFF, c1 & 0xFF
    r = int(round(r0 + (r1 - r0) * t))
    g = int(round(g0 + (g1 - g0) * t))
    b = int(round(b0 + (b1 - b0) * t))
    return (r << 16) | (g << 8) | b


TOOLS: dict[str, Tool] = {
    "single": SingleTool(),
    "rect": RectTool(),
    "bucket": BucketTool(),
    "gradient": GradientTool(),
}
