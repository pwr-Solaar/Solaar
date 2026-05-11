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

"""ANSI QWERTY keyboard layouts (full 104-key and TKL).

Cell positions and groupings derived from OpenRGB's KeyboardLayoutManager
(KeyboardLayoutManager.cpp), Copyright (C) Chris M (Dr_No), licensed under
GPL-2.0-or-later. This file ports the static ANSI data only; the runtime
opcode interpreter for regional overlays is intentionally not included.
"""

from __future__ import annotations

from ..layout import Layout
from ._keyboard_base import MAIN_ANSI
from ._keyboard_base import build_layout

LAYOUT_FULL: Layout = build_layout(
    MAIN_ANSI,
    include_numpad=True,
    description="ANSI QWERTY 104-key full-size",
)


LAYOUT_TKL: Layout = build_layout(
    MAIN_ANSI,
    include_numpad=False,
    description="ANSI QWERTY tenkeyless",
)
