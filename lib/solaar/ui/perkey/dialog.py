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

"""Per-device dialogs hosting a PerKeyEditor.

One dialog instance is kept per device key (firmware unit-id, falling
back to other stable identifiers — see ``get_dialog``). The same
physical device on different transports (receiver vs direct USB) shares
a key so it doesn't open two windows.
"""

from __future__ import annotations

from enum import Enum
from typing import Hashable

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # NOQA: E402

from solaar.i18n import _  # NOQA: E402

from .editor import PerKeyEditor  # NOQA: E402
from .layout import Layout  # NOQA: E402
from .protocol import PerKeyColorSink  # NOQA: E402


class GtkSignal(Enum):
    DELETE_EVENT = "delete-event"


_dialogs: dict[Hashable, "PerKeyEditorDialog"] = {}


class PerKeyEditorDialog:
    def __init__(self, key: Hashable) -> None:
        self._key = key
        self._window: Gtk.Window | None = None
        self._wrapper: Gtk.Box | None = None
        self._editor: PerKeyEditor | None = None
        self._sink: PerKeyColorSink | None = None

    def _on_delete(self, _w, _e) -> bool:
        self._destroy()
        _dialogs.pop(self._key, None)
        return True

    def _destroy(self) -> None:
        if self._editor is not None:
            self._editor.shutdown()
            self._editor = None
        if self._window is not None:
            self._window.destroy()
            self._window = None
            self._wrapper = None
        self._sink = None

    def present(self, sink: PerKeyColorSink, layout: Layout | None) -> None:
        # Re-opening for the same sink while the window is already open:
        # just raise it (no rebuild flicker, preserves any in-progress
        # interaction state).
        if self._window is not None and self._sink is sink:
            self._window.present()
            return
        # Otherwise build a fresh window. We always recreate rather than
        # swap content in place because Gtk.Window.resize() after first
        # show is unreliable across X11/Wayland WMs — the WM often keeps
        # the original geometry — and a new window picks up the layout's
        # natural size cleanly on first show.
        self._destroy()
        self._sink = sink
        self._window = Gtk.Window()
        self._window.set_title(_("Per-key Lighting") + " — " + sink.title)
        self._window.connect(GtkSignal.DELETE_EVENT.value, self._on_delete)
        self._wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._wrapper.set_border_width(8)
        self._window.add(self._wrapper)
        self._editor = PerKeyEditor(sink, layout)
        self._wrapper.pack_start(self._editor, True, True, 0)
        self._wrapper.show_all()
        # Ask GTK what the wrapper actually wants to be — the canvas's
        # size_request propagates up through ScrolledWindow + editor VBox
        # (toolbar + scrolled canvas) + the wrapper's border, so the
        # natural size already accounts for every layout contribution.
        _min, nat = self._wrapper.get_preferred_size()
        if nat.width > 0 and nat.height > 0:
            self._window.resize(nat.width, nat.height)
        self._window.present()


def get_dialog(key: Hashable) -> PerKeyEditorDialog:
    """Return the dialog for `key`, creating one if none is open.

    `key` should be a stable per-device identifier. The caller (control.py)
    builds it from `device.unitId` first — that's read from the device
    firmware via the DeviceInformation feature and is the same regardless
    of whether the device is on a receiver or plugged directly via USB,
    so the same physical device doesn't open two windows when its
    transport changes.
    """
    d = _dialogs.get(key)
    if d is None:
        d = PerKeyEditorDialog(key)
        _dialogs[key] = d
    return d
