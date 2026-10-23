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

"""PRO X RAPID (PRO X TKL RAPID) per-key layout.

Same generated regional main block as any TKL keyboard, plus a customized
media top row. This board wires five dedicated media keys above the F-row with
board-specific zone ids that the canonical extras map (153-158) does not cover;
ids and positions are hardware-probed (ported from the OpenRGB key-map for this
model). The logo has no addressable LED here.
"""

from __future__ import annotations

from ..layout import Cell
from ..layout import Layout

# Dedicated media keys, hardware-probed. Columns align above the F-row
# (F4=col5, F9-F12=cols10-13). Zone ids are board-specific — NOT the canonical
# 153-158 extras — and the logo (canonical 210) is unlit on this model.
# group="media" keeps these out of strip_groups so they render in the matrix.
MEDIA_TOP_ROW: tuple[Cell, ...] = (
    Cell(zone_id=150, row=0, col=5, group="media", label="Bright"),
    Cell(zone_id=155, row=0, col=10, group="media", label="Prev"),
    Cell(zone_id=152, row=0, col=11, group="media", label="Play"),
    Cell(zone_id=154, row=0, col=12, group="media", label="Next"),
    Cell(zone_id=153, row=0, col=13, group="media", label="Mute"),
)


def with_media_top_row(base: Layout) -> Layout:
    """Return `base` with every cell pushed down one row and the PRO X RAPID
    media top row placed at row 0.

    The media keys are explicit bound cells, so they paint directly with no
    EXTRAS_ALLOWLIST entry, while `base`'s `extra_zones` still filters the
    phantom zones this board shares with the G515 (47, 97, 99-103, 254).
    """
    shifted = tuple(
        Cell(
            zone_id=c.zone_id,
            row=c.row + 1,
            col=c.col,
            width=c.width,
            height=c.height,
            group=c.group,
            label=c.label,
            x=c.x,
            y=c.y,
        )
        for c in base.cells
    )
    return Layout(
        cells=MEDIA_TOP_ROW + shifted,
        rows=base.rows + 1,
        cols=base.cols,
        strip_groups=base.strip_groups,
        supported_tools=base.supported_tools,
        extra_zones=base.extra_zones,
        description="PRO X RAPID",
    )
