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

"""Singleton dialog hosting a PerKeyEditor for one sink at a time."""

from __future__ import annotations

from enum import Enum

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # NOQA: E402

from solaar.i18n import _  # NOQA: E402

from .editor import PerKeyEditor  # NOQA: E402
from .layout import Layout  # NOQA: E402
from .protocol import PerKeyColorSink  # NOQA: E402


class GtkSignal(Enum):
    DELETE_EVENT = "delete-event"


class PerKeyEditorDialog:
    _instance: "PerKeyEditorDialog | None" = None

    def __init__(self) -> None:
        self._window = Gtk.Window()
        self._window.set_title(_("Per-key Lighting"))
        # No default size or geometry hints — the editor's content size
        # (driven by KeyboardCanvas's size_request) determines the window size
        # via the ScrolledWindow's propagate_natural_size. Wide keyboards open
        # large; small mice open small.
        self._window.connect(GtkSignal.DELETE_EVENT.value, self._on_delete)
        self._editor: PerKeyEditor | None = None
        self._wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._wrapper.set_border_width(8)
        self._window.add(self._wrapper)

    def _on_delete(self, _w, _e) -> bool:
        self._window.hide()
        if self._editor is not None:
            self._editor.shutdown()
            self._wrapper.remove(self._editor)
            self._editor = None
        return True

    def present(self, sink: PerKeyColorSink, layout: Layout | None) -> None:
        if self._editor is not None:
            self._editor.shutdown()
            self._wrapper.remove(self._editor)
            self._editor = None
        self._editor = PerKeyEditor(sink, layout)
        self._wrapper.pack_start(self._editor, True, True, 0)
        self._wrapper.show_all()
        self._window.set_title(_("Per-key Lighting") + " — " + sink.title)
        # Resize to fit canvas + toolbar. ScrolledWindow's *minimum* is tiny
        # (one row's worth) regardless of propagate_natural_size, so we have
        # to compute the target ourselves from the canvas's size_request.
        canvas_w, canvas_h = self._editor.canvas_size()
        if canvas_w > 0 and canvas_h > 0:
            # Toolbar ~50px, wrapper border 8px each side, scrollbar slack ~4.
            target_w = canvas_w + 32
            target_h = canvas_h + 80
            self._window.resize(target_w, target_h)
        self._window.present()


def get_dialog() -> PerKeyEditorDialog:
    if PerKeyEditorDialog._instance is None:
        PerKeyEditorDialog._instance = PerKeyEditorDialog()
    return PerKeyEditorDialog._instance
