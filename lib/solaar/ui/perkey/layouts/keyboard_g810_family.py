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

"""G810/G610, G910 and G Pro (0x8080) per-key layout variants.

Each variant is a generated regional base plus that model's special-key
strip. Positions and wire ids are ported from the long-shipped legacy
OpenRGB maps for this family (years of field use); the wire (keyType, keyId)
addresses translate to Solaar zones in settings_templates.

Solaar zones used here: 210 logo, 211 nameplate, 240 lighting key, 241 game
mode, 242/243/244 caps/scroll/num lock indicators, 155 play/pause, 156 mute,
157 next, 158 previous, 159 stop, 180-188 G1-G9.
"""

from __future__ import annotations

from ..layout import Cell
from ..layout import Layout


def _shifted(cells: tuple[Cell, ...], drow: int = 0, dcol: int = 0) -> tuple[Cell, ...]:
    return tuple(
        Cell(
            zone_id=c.zone_id,
            row=c.row + drow,
            col=c.col + dcol,
            width=c.width,
            height=c.height,
            group=c.group,
            label=c.label,
            x=c.x,
            y=c.y,
        )
        for c in cells
    )


# --- G810 / G610: logo, indicator row and Mute above the F-row, media block
#     (play / stop / previous / next) in the F-row line right of Pause.
G810_TOP_STRIP: tuple[Cell, ...] = (
    Cell(zone_id=210, row=0, col=0, group="extras", label="Logo"),
    Cell(zone_id=244, row=0, col=12, group="extras", label="Num"),
    Cell(zone_id=242, row=0, col=13, group="extras", label="Caps"),
    Cell(zone_id=243, row=0, col=14, group="extras", label="Scroll"),
    Cell(zone_id=241, row=0, col=16, group="extras", label="Game"),
    Cell(zone_id=240, row=0, col=18, group="extras", label="Light"),
    Cell(zone_id=156, row=0, col=19, group="extras", label="Mute"),
    Cell(zone_id=155, row=1, col=17, group="extras", label="Play"),
    Cell(zone_id=159, row=1, col=18, group="extras", label="Stop"),
    Cell(zone_id=158, row=1, col=19, group="extras", label="Prev"),
    Cell(zone_id=157, row=1, col=20, group="extras", label="Next"),
)


def g810_layout(base: Layout) -> Layout:
    """Full-size `base` pushed down one row, G810/G610 strip on top."""
    return Layout(
        cells=G810_TOP_STRIP + _shifted(base.cells, drow=1),
        rows=base.rows + 1,
        cols=base.cols,
        strip_groups=base.strip_groups,
        supported_tools=base.supported_tools,
        extra_zones=base.extra_zones,
        description="G810/G610",
    )


# --- G910: G6-G9 in a row directly above F1-F4, Logo left of Esc in the
#     F-row, G1-G5 down the left edge, Nameplate on the front edge. The
#     media cluster is deliberately absent (on/off backlight, not RGB —
#     the firmware still over-advertises the media keyType) and the four
#     small mode keys left of G6 have no identified wire ids; anything the
#     firmware does enumerate for them surfaces in the bottom strip.
G910_SIDE_STRIP: tuple[Cell, ...] = (
    Cell(zone_id=185, row=0, col=3, group="extras", label="G6"),
    Cell(zone_id=186, row=0, col=4, group="extras", label="G7"),
    Cell(zone_id=187, row=0, col=5, group="extras", label="G8"),
    Cell(zone_id=188, row=0, col=6, group="extras", label="G9"),
    Cell(zone_id=210, row=1, col=0, group="extras", label="Logo"),
    Cell(zone_id=180, row=2, col=0, group="extras", label="G1"),
    Cell(zone_id=181, row=3, col=0, group="extras", label="G2"),
    Cell(zone_id=182, row=4, col=0, group="extras", label="G3"),
    Cell(zone_id=183, row=5, col=0, group="extras", label="G4"),
    Cell(zone_id=184, row=6, col=0, group="extras", label="G5"),
    Cell(zone_id=211, row=7, col=4, width=5.0, group="extras", label="Nameplate"),
)


def g910_layout(base: Layout) -> Layout:
    """Full-size `base` pushed down one row and right one column, G910
    G-key column / logo / nameplate placed around it."""
    return Layout(
        cells=G910_SIDE_STRIP + _shifted(base.cells, drow=1, dcol=1),
        rows=base.rows + 2,  # +1 G6-G9 row on top, +1 nameplate row below
        cols=base.cols + 1,  # +1 G1-G5 / logo column on the left
        strip_groups=base.strip_groups,
        supported_tools=base.supported_tools,
        extra_zones=base.extra_zones,
        description="G910",
    )


# --- G Pro (wired TKL): logo and indicator row above the F-row; no media
#     keys and no Num Lock indicator on this board.
GPRO_TOP_STRIP: tuple[Cell, ...] = (
    Cell(zone_id=210, row=0, col=0, group="extras", label="Logo"),
    Cell(zone_id=242, row=0, col=12, group="extras", label="Caps"),
    Cell(zone_id=243, row=0, col=13, group="extras", label="Scroll"),
    Cell(zone_id=241, row=0, col=15, group="extras", label="Game"),
    Cell(zone_id=240, row=0, col=16, group="extras", label="Light"),
)


def gpro_layout(base: Layout) -> Layout:
    """TKL `base` pushed down one row, G Pro strip on top."""
    return Layout(
        cells=GPRO_TOP_STRIP + _shifted(base.cells, drow=1),
        rows=base.rows + 1,
        cols=base.cols,
        strip_groups=base.strip_groups,
        supported_tools=base.supported_tools,
        extra_zones=base.extra_zones,
        description="G PRO",
    )
