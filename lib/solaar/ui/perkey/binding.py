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

"""Bind a Layout to a sink's reported zone list.

Cells whose `zone_id` the device reports are marked bound. Cells whose zone
the device does not report stay disabled (greyed). Device-reported zones not
covered by any cell get synthesized as strip cells using the sink's labels —
this catches G-keys, logo, media keys and any device-specific extras.
"""

from __future__ import annotations

from collections.abc import Callable

from .layout import BoundCell
from .layout import BoundLayout
from .layout import Cell
from .layout import Layout


def bind(layout: Layout, zones: list[int], label_for: Callable[[int], str]) -> BoundLayout:
    reported = set(zones)
    claimed: set[int] = set()
    matrix: list[BoundCell] = []
    strip: list[BoundCell] = []
    for c in layout.matrix_cells():
        bound = c.zone_id in reported
        if bound:
            claimed.add(c.zone_id)
        matrix.append(BoundCell(cell=c, bound=bound))
    for c in layout.strip_cells():
        bound = c.zone_id in reported
        if bound:
            claimed.add(c.zone_id)
        strip.append(BoundCell(cell=c, bound=bound))
    unmapped_all = tuple(z for z in zones if z not in claimed)
    # Filter unmapped zones through the layout's curated allowlist. Without
    # this, firmware-reported phantoms (G515 reports 47, 97, 99-103, 254)
    # would surface as paintable strip cells that don't address any LED.
    if layout.extra_zones is None:
        showable = unmapped_all
    else:
        showable = tuple(z for z in unmapped_all if z in layout.extra_zones)
    next_col = max((bc.cell.col for bc in strip), default=-1) + 1
    for z in showable:
        synth = Cell(zone_id=z, row=0, col=next_col, group="strip", label=label_for(z))
        strip.append(BoundCell(cell=synth, bound=True))
        next_col += 1
    return BoundLayout(matrix=tuple(matrix), strip=tuple(strip), unmapped=unmapped_all)
