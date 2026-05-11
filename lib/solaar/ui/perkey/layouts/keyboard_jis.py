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

"""JIS layout (JP).

ISO shape with Japanese keycap relabels for the bracket / colon positions.
Adapted from OpenRGB. JIS keyboards also have additional kana-control keys
near the spacebar (henkan/muhenkan/kana) that aren't represented here —
matches OpenRGB's coverage.
"""

from __future__ import annotations

from ..layout import Layout
from ._keyboard_base import MAIN_ISO
from ._keyboard_base import build_layout

# zone_id → JIS label
_OVERRIDES: dict[int, str] = {
    44: "@",  # row 2 col 11 — bracket-position becomes at-sign
    45: "[",  # row 2 col 12 — bracket shifts left
    49: ":",  # row 3 col 11 — quote-position becomes colon
}


LAYOUT_FULL: Layout = build_layout(
    MAIN_ISO,
    include_numpad=True,
    label_overrides=_OVERRIDES,
    description="JIS (JP) full-size",
)


LAYOUT_TKL: Layout = build_layout(
    MAIN_ISO,
    include_numpad=False,
    label_overrides=_OVERRIDES,
    description="JIS (JP) tenkeyless",
)
