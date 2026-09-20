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

"""GUI editor for onboard-profile button assignments.

Devices that remap their extra buttons through the ``ONBOARD_PROFILES``
feature (most gaming mice, e.g. the G502 X family) have no host-side
``REPROG_CONTROLS`` / ``PERSISTENT_REMAPPABLE_ACTION`` feature for Solaar's
existing ``MapChoiceControl`` to hook into -- button assignments live in
onboard flash instead, and were previously only reachable through
``solaar profiles <device> [file]`` on the command line.

This package adds a small GTK dialog, opened from the settings panel like
the per-key RGB editor, that lets a user capture a keyboard key and assign
it to one button slot of the active onboard profile without hand-editing
YAML.

Scope (v1): keyboard-key assignments only (``Button`` behavior ``SEND`` /
type ``MODIFIER_AND_KEY``), plus clearing a slot back to unassigned.
Mouse-button emulation, consumer keys, and device functions (DPI cycle,
profile switch, G-Shift, ...) are intentionally out of scope for now --
those are still only editable via the CLI YAML round trip.
"""

from __future__ import annotations

__all__ = ()
