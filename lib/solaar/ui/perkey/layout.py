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

"""Visual layout primitives for the per-key color editor.

This module is pure data. It does not import GTK and does not import from
`lib.logitech_receiver`. It is therefore relocatable into a shared package
when the frontend/backend split happens.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field


@dataclass(frozen=True)
class Cell:
    """One paintable cell in a layout.

    `zone_id` is the firmware identifier the device uses for this LED. It is
    matched against the device's reported zone list at bind time; cells with
    no matching device zone are drawn disabled.
    """

    zone_id: int
    row: int
    col: int
    width: float = 1.0
    height: float = 1.0
    group: str = "main"
    label: str = ""
    x: float | None = None
    y: float | None = None


@dataclass(frozen=True)
class Layout:
    """A device-class visual layout.

    Cells in `strip_groups` are rendered as a flat row beneath the matrix
    region, regardless of their row/col fields. Cells outside `strip_groups`
    are placed by row/col on the main matrix.

    `extra_zones` is a curated allowlist of zone ids that may appear in the
    bottom strip when the device reports them but they are not covered by a
    layout cell. Zones outside the allowlist are dropped — Logitech firmware
    bitmaps enumerate phantom/reserved slots (e.g. G515 reports 47, 97, 99-103,
    254) that aren't physical keys. Set to `None` to disable filtering.
    """

    cells: tuple[Cell, ...]
    rows: int
    cols: int
    strip_groups: tuple[str, ...] = ("strip",)
    supported_tools: tuple[str, ...] = ("single", "rect", "bucket", "gradient")
    extra_zones: frozenset[int] | None = None
    description: str = ""

    def matrix_cells(self) -> tuple[Cell, ...]:
        return tuple(c for c in self.cells if c.group not in self.strip_groups)

    def strip_cells(self) -> tuple[Cell, ...]:
        return tuple(c for c in self.cells if c.group in self.strip_groups)

    def by_zone(self) -> dict[int, Cell]:
        return {c.zone_id: c for c in self.cells}


@dataclass(frozen=True)
class BoundCell:
    """A Cell augmented with bind state, returned by `binding.bind`."""

    cell: Cell
    bound: bool


@dataclass(frozen=True)
class BoundLayout:
    """Result of binding a Layout against a sink's reported zones.

    `matrix` and `strip` are tuples of BoundCell in render order. `unmapped`
    holds zones the device reported that no Layout cell claimed; these get
    appended to the strip with synthesized cells.
    """

    matrix: tuple[BoundCell, ...] = field(default_factory=tuple)
    strip: tuple[BoundCell, ...] = field(default_factory=tuple)
    unmapped: tuple[int, ...] = field(default_factory=tuple)
