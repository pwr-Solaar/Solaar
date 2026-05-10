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

"""ANSI QWERTY keyboard layouts (full 104-key and TKL).

Cell positions and groupings derived from OpenRGB's KeyboardLayoutManager
(KeyboardLayoutManager.cpp), Copyright (C) Chris M (Dr_No), licensed under
GPL-2.0-or-later. This file ports the static ANSI data only; the runtime
opcode interpreter for regional overlays is intentionally not included.

Zone IDs are the firmware values reported by Logitech HID++ feature 0x8081
(PER_KEY_LIGHTING_V2).
"""

from __future__ import annotations

from ..layout import Cell
from ..layout import Layout

# Main alpha block (KLM keyboard_zone_main, ANSI variant).
# ANSI removes the ISO backslash (row 4 col 1) and POUND (row 3 col 12).
_MAIN: tuple[Cell, ...] = (
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

# Function row (KLM keyboard_zone_fn_row): ESC + F1..F12.
_FN_ROW: tuple[Cell, ...] = (
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

# Extras cluster (KLM keyboard_zone_extras): nav block + arrows.
_EXTRAS: tuple[Cell, ...] = (
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

# Numpad (KLM keyboard_zone_numpad). NumPad + and Enter span 2 rows tall.
_NUMPAD: tuple[Cell, ...] = (
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


# Curated allowlist for unmapped device zones surfaced in the bottom strip.
# Mirrors OpenRGB's `hidpp20_key_name_to_zone` extras: brightness, media,
# G1-G5, logo. Anything else (e.g. G515 phantoms 47, 97, 99-103, 254) is
# dropped by the binder.
_EXTRAS_ALLOWLIST: frozenset[int] = frozenset(
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


LAYOUT_FULL: Layout = Layout(
    cells=_FN_ROW + _MAIN + _EXTRAS + _NUMPAD,
    rows=6,
    cols=21,
    extra_zones=_EXTRAS_ALLOWLIST,
    description="ANSI QWERTY 104-key full-size",
)


LAYOUT_TKL: Layout = Layout(
    cells=_FN_ROW + _MAIN + _EXTRAS,
    rows=6,
    cols=17,
    extra_zones=_EXTRAS_ALLOWLIST,
    description="ANSI QWERTY tenkeyless",
)
