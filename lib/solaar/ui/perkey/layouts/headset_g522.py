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

"""LED layout for the G522 LIGHTSPEED headset.

Eight LEDs in two 2×2 grids — one per earcup, viewed from outside:

    Left earcup          Right earcup
    ┌─────┬─────┐        ┌─────┬─────┐
    │  8  │  7  │        │  6  │  5  │
    ├─────┼─────┤        ├─────┼─────┤
    │  4  │  3  │        │  2  │  1  │
    └─────┴─────┘        └─────┴─────┘
"""

from __future__ import annotations

from ..layout import Cell
from ..layout import Layout

_CELLS: tuple[Cell, ...] = (
    # Left earcup (cols 0-1, outer view): top-left=8, top-right=7, bottom-left=4, bottom-right=3
    Cell(zone_id=8, row=0, col=0, group="main", label="8"),
    Cell(zone_id=7, row=0, col=1, group="main", label="7"),
    Cell(zone_id=4, row=1, col=0, group="main", label="4"),
    Cell(zone_id=3, row=1, col=1, group="main", label="3"),
    # Right earcup (cols 3-4, outer view): top-left=6, top-right=5, bottom-left=2, bottom-right=1
    Cell(zone_id=6, row=0, col=3, group="main", label="6"),
    Cell(zone_id=5, row=0, col=4, group="main", label="5"),
    Cell(zone_id=2, row=1, col=3, group="main", label="2"),
    Cell(zone_id=1, row=1, col=4, group="main", label="1"),
)


LAYOUT: Layout = Layout(
    cells=_CELLS,
    rows=2,
    cols=5,
    description="Logitech G522 LIGHTSPEED headset (8 LEDs, 4 per earcup)",
)
