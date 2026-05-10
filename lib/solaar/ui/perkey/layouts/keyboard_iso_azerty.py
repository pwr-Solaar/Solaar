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

"""ISO AZERTY layout (FR).

ISO shape plus French label overrides — A↔Q, W↔Z, M repositioned, French
digit-row symbols (& é " ' ( - è _ ç à ). Adapted from OpenRGB.
"""

from __future__ import annotations

from ..layout import Layout
from ._keyboard_base import MAIN_ISO
from ._keyboard_base import build_layout

# zone_id → French label
_OVERRIDES: dict[int, str] = {
    # Row 1 (digit row → French symbols)
    50: "²",  # backtick → super-2
    27: "&",  # 1
    28: "é",  # 2
    29: '"',  # 3
    30: "'",  # 4
    31: "(",  # 5
    32: "-",  # 6
    33: "è",  # 7
    34: "_",  # 8
    35: "ç",  # 9
    36: "à",  # 0
    42: ")",  # minus → close-paren
    # Row 2 — Q/A and W/Z swaps, brackets relabeled
    17: "A",  # Q-position → A
    23: "Z",  # W-position → Z
    44: "^",  # [-position → caret
    45: "$",  # ]-position → dollar
    # Row 3 — A → Q; M moves up to ; position
    1: "Q",  # A-position → Q
    48: "M",  # ;-position → M
    49: "ù",  # '-position → ù
    # Row 4 — Z-position becomes W; comma row shifts
    26: "W",  # Z-position → W
    13: ",",  # M-position → comma
    51: ";",  # ,-position → semicolon
    52: ":",  # .-position → colon
    53: "!",  # /-position → exclamation
}


LAYOUT_FULL: Layout = build_layout(
    MAIN_ISO,
    include_numpad=True,
    label_overrides=_OVERRIDES,
    description="ISO AZERTY (FR) full-size",
)


LAYOUT_TKL: Layout = build_layout(
    MAIN_ISO,
    include_numpad=False,
    label_overrides=_OVERRIDES,
    description="ISO AZERTY (FR) tenkeyless",
)
