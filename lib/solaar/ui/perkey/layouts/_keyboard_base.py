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

"""Shared building blocks for regional keyboard layouts.

Each region (ANSI, ISO_QWERTY, ISO_QWERTZ, ISO_AZERTY, JIS) shares the function
row, nav-cluster, and numpad blocks; only the main alpha block differs (ANSI
includes the row 2 col 13 backslash, ISO doesn't). Regional label overrides on
top of either main block produce the final layout.

Cell positions and groupings adapted from OpenRGB's KeyboardLayoutManager.
Zone IDs are firmware values reported by Logitech HID++ feature 0x8081
(PER_KEY_LIGHTING_V2).
"""

from __future__ import annotations

from ..layout import Cell
from ..layout import Layout

# --- Function row: ESC + F1..F12 (shared across all regions).
FN_ROW: tuple[Cell, ...] = (
    Cell(zone_id=38, row=0, col=0, group="fn_row", label="Esc"),
    Cell(zone_id=55, row=0, col=2, group="fn_row", label="F1"),
    Cell(zone_id=56, row=0, col=3, group="fn_row", label="F2"),
    Cell(zone_id=57, row=0, col=4, group="fn_row", label="F3"),
    Cell(zone_id=58, row=0, col=5, group="fn_row", label="F4"),
    Cell(zone_id=59, row=0, col=6, group="fn_row", label="F5"),
    Cell(zone_id=60, row=0, col=7, group="fn_row", label="F6"),
    Cell(zone_id=61, row=0, col=8, group="fn_row", label="F7"),
    Cell(zone_id=62, row=0, col=9, group="fn_row", label="F8"),
    Cell(zone_id=63, row=0, col=10, group="fn_row", label="F9"),
    Cell(zone_id=64, row=0, col=11, group="fn_row", label="F10"),
    Cell(zone_id=65, row=0, col=12, group="fn_row", label="F11"),
    Cell(zone_id=66, row=0, col=13, group="fn_row", label="F12"),
)

# --- Nav cluster + arrows (shared).
EXTRAS: tuple[Cell, ...] = (
    Cell(zone_id=67, row=0, col=14, group="extras", label="PrtSc"),
    Cell(zone_id=68, row=0, col=15, group="extras", label="ScrLk"),
    Cell(zone_id=69, row=0, col=16, group="extras", label="Pause"),
    Cell(zone_id=70, row=1, col=14, group="extras", label="Ins"),
    Cell(zone_id=71, row=1, col=15, group="extras", label="Home"),
    Cell(zone_id=72, row=1, col=16, group="extras", label="PgUp"),
    Cell(zone_id=73, row=2, col=14, group="extras", label="Del"),
    Cell(zone_id=74, row=2, col=15, group="extras", label="End"),
    Cell(zone_id=75, row=2, col=16, group="extras", label="PgDn"),
    Cell(zone_id=79, row=4, col=15, group="extras", label="↑"),
    Cell(zone_id=77, row=5, col=14, group="extras", label="←"),
    Cell(zone_id=78, row=5, col=15, group="extras", label="↓"),
    Cell(zone_id=76, row=5, col=16, group="extras", label="→"),
)

# --- Numpad block (only on full-size keyboards).
NUMPAD: tuple[Cell, ...] = (
    Cell(zone_id=80, row=1, col=17, group="numpad", label="Num"),
    Cell(zone_id=81, row=1, col=18, group="numpad", label="/"),
    Cell(zone_id=82, row=1, col=19, group="numpad", label="*"),
    Cell(zone_id=83, row=1, col=20, group="numpad", label="-"),
    Cell(zone_id=92, row=2, col=17, group="numpad", label="7"),
    Cell(zone_id=93, row=2, col=18, group="numpad", label="8"),
    Cell(zone_id=94, row=2, col=19, group="numpad", label="9"),
    Cell(zone_id=84, row=2, col=20, height=2.0, group="numpad", label="+"),
    Cell(zone_id=89, row=3, col=17, group="numpad", label="4"),
    Cell(zone_id=90, row=3, col=18, group="numpad", label="5"),
    Cell(zone_id=91, row=3, col=19, group="numpad", label="6"),
    Cell(zone_id=86, row=4, col=17, group="numpad", label="1"),
    Cell(zone_id=87, row=4, col=18, group="numpad", label="2"),
    Cell(zone_id=88, row=4, col=19, group="numpad", label="3"),
    Cell(zone_id=85, row=4, col=20, height=2.0, group="numpad", label="Enter"),
    Cell(zone_id=95, row=5, col=17, width=2.0, group="numpad", label="0"),
    Cell(zone_id=96, row=5, col=19, group="numpad", label="."),
)

# --- Main alpha block, ANSI (104-key). Includes row 2 col 13 backslash and
#     omits POUND (row 3 col 12) + ISO_BACKSLASH (row 4 col 1).
MAIN_ANSI: tuple[Cell, ...] = (
    # Row 1: backtick + numbers + minus/equals + backspace
    Cell(zone_id=50, row=1, col=0, group="main", label="`"),
    Cell(zone_id=27, row=1, col=1, group="main", label="1"),
    Cell(zone_id=28, row=1, col=2, group="main", label="2"),
    Cell(zone_id=29, row=1, col=3, group="main", label="3"),
    Cell(zone_id=30, row=1, col=4, group="main", label="4"),
    Cell(zone_id=31, row=1, col=5, group="main", label="5"),
    Cell(zone_id=32, row=1, col=6, group="main", label="6"),
    Cell(zone_id=33, row=1, col=7, group="main", label="7"),
    Cell(zone_id=34, row=1, col=8, group="main", label="8"),
    Cell(zone_id=35, row=1, col=9, group="main", label="9"),
    Cell(zone_id=36, row=1, col=10, group="main", label="0"),
    Cell(zone_id=42, row=1, col=11, group="main", label="-"),
    Cell(zone_id=43, row=1, col=12, group="main", label="="),
    Cell(zone_id=39, row=1, col=13, group="main", label="Bksp"),
    # Row 2: tab + qwerty + brackets + backslash
    Cell(zone_id=40, row=2, col=0, group="main", label="Tab"),
    Cell(zone_id=17, row=2, col=1, group="main", label="Q"),
    Cell(zone_id=23, row=2, col=2, group="main", label="W"),
    Cell(zone_id=5, row=2, col=3, group="main", label="E"),
    Cell(zone_id=18, row=2, col=4, group="main", label="R"),
    Cell(zone_id=20, row=2, col=5, group="main", label="T"),
    Cell(zone_id=25, row=2, col=6, group="main", label="Y"),
    Cell(zone_id=21, row=2, col=7, group="main", label="U"),
    Cell(zone_id=9, row=2, col=8, group="main", label="I"),
    Cell(zone_id=15, row=2, col=9, group="main", label="O"),
    Cell(zone_id=16, row=2, col=10, group="main", label="P"),
    Cell(zone_id=44, row=2, col=11, group="main", label="["),
    Cell(zone_id=45, row=2, col=12, group="main", label="]"),
    Cell(zone_id=46, row=2, col=13, group="main", label="\\"),
    # Row 3: caps + asdf-row + semi/quote + enter
    Cell(zone_id=54, row=3, col=0, group="main", label="Caps"),
    Cell(zone_id=1, row=3, col=1, group="main", label="A"),
    Cell(zone_id=19, row=3, col=2, group="main", label="S"),
    Cell(zone_id=4, row=3, col=3, group="main", label="D"),
    Cell(zone_id=6, row=3, col=4, group="main", label="F"),
    Cell(zone_id=7, row=3, col=5, group="main", label="G"),
    Cell(zone_id=8, row=3, col=6, group="main", label="H"),
    Cell(zone_id=10, row=3, col=7, group="main", label="J"),
    Cell(zone_id=11, row=3, col=8, group="main", label="K"),
    Cell(zone_id=12, row=3, col=9, group="main", label="L"),
    Cell(zone_id=48, row=3, col=10, group="main", label=";"),
    Cell(zone_id=49, row=3, col=11, group="main", label="'"),
    Cell(zone_id=37, row=3, col=13, group="main", label="Enter"),
    # Row 4: shift + zxcv-row + comma/period/slash + rshift
    Cell(zone_id=105, row=4, col=0, group="main", label="Shift"),
    Cell(zone_id=26, row=4, col=2, group="main", label="Z"),
    Cell(zone_id=24, row=4, col=3, group="main", label="X"),
    Cell(zone_id=3, row=4, col=4, group="main", label="C"),
    Cell(zone_id=22, row=4, col=5, group="main", label="V"),
    Cell(zone_id=2, row=4, col=6, group="main", label="B"),
    Cell(zone_id=14, row=4, col=7, group="main", label="N"),
    Cell(zone_id=13, row=4, col=8, group="main", label="M"),
    Cell(zone_id=51, row=4, col=9, group="main", label=","),
    Cell(zone_id=52, row=4, col=10, group="main", label="."),
    Cell(zone_id=53, row=4, col=11, group="main", label="/"),
    Cell(zone_id=109, row=4, col=13, group="main", label="Shift"),
    # Row 5: bottom row. Space spans cols 3..9 visually.
    Cell(zone_id=104, row=5, col=0, group="main", label="Ctrl"),
    Cell(zone_id=107, row=5, col=1, group="main", label="Win"),
    Cell(zone_id=106, row=5, col=2, group="main", label="Alt"),
    Cell(zone_id=41, row=5, col=3, width=7.0, group="main", label="Space"),
    Cell(zone_id=110, row=5, col=10, group="main", label="AltGr"),
    Cell(zone_id=111, row=5, col=11, group="main", label="Win"),
    Cell(zone_id=98, row=5, col=12, group="main", label="Menu"),
    Cell(zone_id=108, row=5, col=13, group="main", label="Ctrl"),
)

# --- Main alpha block, ISO. Same as ANSI minus the row 2 col 13 backslash;
#     on ISO that position is the top half of the L-shape Enter, addressed
#     by zone 37 (the main Enter cell at row 3 col 13). Zone 46 is silently
#     unaddressable on ISO layouts — same limitation as OpenRGB's UI.
MAIN_ISO: tuple[Cell, ...] = tuple(c for c in MAIN_ANSI if not (c.row == 2 and c.col == 13))

# --- Curated allowlist for unmapped device zones surfaced in the bottom strip.
#     G-keys, logo, media, brightness — the canonical "extras" Logitech firmware
#     actually addresses. Phantom zones (e.g. G515's 47, 97, 99-103, 254) drop.
EXTRAS_ALLOWLIST: frozenset[int] = frozenset(
    {
        153,  # Brightness
        155,  # Play/Pause
        156,  # Mute
        157,  # Next
        158,  # Previous
        180,  # G1
        181,  # G2
        182,  # G3
        183,  # G4
        184,  # G5
        210,  # Logo
    }
)


def _relabel(cells: tuple[Cell, ...], overrides: dict[int, str]) -> tuple[Cell, ...]:
    """Return a new tuple where any cell whose zone_id is in `overrides` has
    its label replaced. Unaffected cells pass through unchanged.
    """
    if not overrides:
        return cells
    return tuple(
        Cell(
            zone_id=c.zone_id,
            row=c.row,
            col=c.col,
            width=c.width,
            height=c.height,
            group=c.group,
            label=overrides[c.zone_id] if c.zone_id in overrides else c.label,
            x=c.x,
            y=c.y,
        )
        for c in cells
    )


def build_layout(
    main_cells: tuple[Cell, ...],
    *,
    include_numpad: bool,
    label_overrides: dict[int, str] | None = None,
    description: str = "",
) -> Layout:
    """Assemble a regional keyboard layout from a chosen main block + the
    shared fn-row / extras / (optionally) numpad blocks. Apply per-zone
    label overrides to every cell whose zone matches.
    """
    cells = FN_ROW + main_cells + EXTRAS
    if include_numpad:
        cells = cells + NUMPAD
    cells = _relabel(cells, label_overrides or {})
    cols = 21 if include_numpad else 17
    return Layout(
        cells=cells,
        rows=6,
        cols=cols,
        extra_zones=EXTRAS_ALLOWLIST,
        description=description,
    )
