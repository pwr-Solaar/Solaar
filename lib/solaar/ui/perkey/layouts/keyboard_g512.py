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

"""G512/G513 (0x8080) per-key layout: generated regional full-size base plus
the two wired indicator LEDs.

The G512 enumerates the full G810-family superset (five indicators, five
international ids) but physically wires only two indicators — caps lock
(0x40/0x03) above Num Lock and game mode (0x40/0x02) above numpad divide
(positions and ids hardware-reported on a G512 ABNT2). Other 0x8080 models
carry different extras; see keyboard_g810_family for the G810/G610, G910
and G Pro variants.
"""

from __future__ import annotations

from ..layout import Cell
from ..layout import Layout

# Solaar zones: 242 = caps lock indicator, 241 = game mode indicator.
# Row 0 cols 17-18 sit above NumLock / numpad divide in the full-size grid.
INDICATOR_CELLS: tuple[Cell, ...] = (
    Cell(zone_id=242, row=0, col=17, group="extras", label="Caps"),
    Cell(zone_id=241, row=0, col=18, group="extras", label="Game"),
)


def with_indicators(base: Layout) -> Layout:
    """Return the full-size `base` with the G512's two indicator LEDs placed
    at their physical position. As explicit cells they leave the bottom strip;
    the unwired superset ids (240/243/244) stay strip-only via the allowlist.
    """
    return Layout(
        cells=base.cells + INDICATOR_CELLS,
        rows=base.rows,
        cols=base.cols,
        strip_groups=base.strip_groups,
        supported_tools=base.supported_tools,
        extra_zones=base.extra_zones,
        description="G512",
    )
