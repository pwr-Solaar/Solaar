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

"""LED layout for the G502 X family (G502 X, G502 X PLUS, G502 X LIGHTSPEED).

Eight LEDs (A..H) reported as zones 1..8 by the firmware. Positions may
need revision per actual hardware.

    Row 0:  C  .  .  .  .  .  B
    Row 1:  .  D  H  G  F  E  .
    Row 2:  .  .  .  .  .  .  A
"""

from __future__ import annotations

from ..layout import Cell
from ..layout import Layout

_CELLS: tuple[Cell, ...] = (
    Cell(zone_id=1, row=2, col=6, group="main", label="A"),
    Cell(zone_id=2, row=0, col=6, group="main", label="B"),
    Cell(zone_id=3, row=0, col=0, group="main", label="C"),
    Cell(zone_id=4, row=1, col=1, group="main", label="D"),
    Cell(zone_id=5, row=1, col=5, group="main", label="E"),
    Cell(zone_id=6, row=1, col=4, group="main", label="F"),
    Cell(zone_id=7, row=1, col=3, group="main", label="G"),
    Cell(zone_id=8, row=1, col=2, group="main", label="H"),
)


LAYOUT: Layout = Layout(
    cells=_CELLS,
    rows=3,
    cols=7,
    description="Logitech G502 X family",
)
