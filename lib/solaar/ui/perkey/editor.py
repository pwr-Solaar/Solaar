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

"""Editor widget: combines toolbar + palette + canvas into one VBox.

The editor consumes only the PerKeyColorSink protocol — no device imports,
no Setting imports — preserving the FE/BE seam.
"""

from __future__ import annotations

import logging

from enum import Enum

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # NOQA: E402

from solaar.i18n import _  # NOQA: E402

from . import binding  # NOQA: E402
from ._icons import attach_themed_icon  # NOQA: E402
from .canvas import KeyboardCanvas  # NOQA: E402
from .layout import Layout  # NOQA: E402
from .macros import MacroEditor  # NOQA: E402
from .palette import GradientSwatch  # NOQA: E402
from .palette import Palette  # NOQA: E402
from .palette import UNSET_COLOR  # NOQA: E402
from .protocol import PerKeyColorSink  # NOQA: E402

logger = logging.getLogger(__name__)


class GtkSignal(Enum):
    CLICKED = "clicked"
    COLOR_CHANGED = "color-changed"
    PAINT = "paint"
    TOGGLED = "toggled"


_TOOL_LABELS = {
    "single": (_("Brush"), _("Click or drag to paint individual keys")),
    "rect": (_("Rect"), _("Drag to select a rectangle of keys, painted on release")),
    "bucket": (_("Fill"), _("Flood-fill connected keys of the same color with the active color")),
}
_TOOL_TOOLTIPS = {
    "gradient": _("Drag to fade from previous color to active color"),
}
_TOOL_ICON_NAMES = {
    "single": "solaar-tool-brush-symbolic",
    "rect": "solaar-tool-rect-symbolic",
    "bucket": "solaar-tool-bucket-symbolic",
}


class PerKeyEditor(Gtk.Box):
    def __init__(self, sink: PerKeyColorSink, layout: Layout | None = None, device=None) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._sink = sink
        self._layout = layout
        self._device = device
        self._unsubscribe = None

        # toolbar row
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._tool_buttons: dict[str, Gtk.RadioButton] = {}
        self._gradient_swatch: GradientSwatch | None = None
        first: Gtk.RadioButton | None = None
        supported = layout.supported_tools if layout else ("single", "rect", "bucket", "gradient")
        for name in supported:
            if name == "gradient":
                btn = Gtk.RadioButton.new_from_widget(first)
                btn.set_mode(False)
                self._gradient_swatch = GradientSwatch()
                btn.add(self._gradient_swatch)
                btn.set_tooltip_text(_TOOL_TOOLTIPS["gradient"])
            else:
                label, tip = _TOOL_LABELS.get(name, (name, ""))
                icon_name = _TOOL_ICON_NAMES.get(name)
                btn = Gtk.RadioButton.new_from_widget(first)
                btn.set_mode(False)  # render as toggle button rather than radio
                if icon_name and attach_themed_icon(btn, icon_name) is not None:
                    btn.set_tooltip_text(tip or label)
                    btn.get_accessible().set_name(label)
                else:
                    btn.set_label(label)
                    btn.set_tooltip_text(tip)
            btn.connect(GtkSignal.TOGGLED.value, self._on_tool_toggled, name)
            if first is None:
                first = btn
            toolbar.pack_start(btn, False, False, 0)
            self._tool_buttons[name] = btn

        # Macro assignment for the device's G-keys.
        macros_btn = Gtk.Button(label=_("Macros…"))
        macros_btn.set_tooltip_text(_("Record a key sequence and assign it to a G-key (G1-G5)"))
        macros_btn.connect(GtkSignal.CLICKED.value, self._on_macros)
        toolbar.pack_start(macros_btn, False, False, 0)

        # Bulk actions. "Colour all" paints every key with the current colour
        # in one click; single keys can then be painted over it (override),
        # leaving the general colour on the rest. "Clear" resets every key back
        # to the general (base) colour.
        fill_all = Gtk.Button()
        if attach_themed_icon(fill_all, "solaar-tool-fillall-symbolic") is not None:
            fill_all.get_accessible().set_name(_("Colour all"))
        else:
            fill_all.set_label(_("Colour all"))
        fill_all.set_tooltip_text(_("Paint every key on the layout with the current colour. Individual keys can then be overridden."))
        fill_all.connect(GtkSignal.CLICKED.value, self._on_fill_all)
        toolbar.pack_end(fill_all, False, False, 0)

        clear_all = Gtk.Button()
        if attach_themed_icon(clear_all, "solaar-tool-clear-symbolic") is not None:
            clear_all.get_accessible().set_name(_("Clear"))
        else:
            clear_all.set_label(_("Clear"))
        clear_all.set_tooltip_text(_("Reset every key back to the general (base) colour"))
        clear_all.connect(GtkSignal.CLICKED.value, self._on_clear_all)
        toolbar.pack_end(clear_all, False, False, 0)

        initial_active, initial_previous = 0xFF0000, 0xFF0000
        try:
            persisted = sink.palette_state()
        except Exception as e:
            logger.debug("palette_state read failed: %s", e)
            persisted = None
        if persisted is not None:
            initial_active, initial_previous = persisted
        self._palette = Palette(active=initial_active, previous=initial_previous)
        self._palette.connect(GtkSignal.COLOR_CHANGED.value, self._on_color_changed)
        toolbar.pack_end(self._palette, False, False, 0)
        if self._gradient_swatch is not None:
            self._gradient_swatch.update(self._palette.get_color(), self._palette.get_last_color())

        self.pack_start(toolbar, False, False, 0)

        # Compact legend so the editor is self-explanatory: how to paint, and
        # where the macro / G-keys live (they are the strip below the main
        # matrix and are individually selectable like every other key).
        legend = Gtk.Label(
            label=_(
                "Paint keys with the current colour. "
                "G and macro keys are in the strip below the main layout and are selected like any other key."
            )
        )
        legend.set_xalign(0.0)
        legend.set_line_wrap(True)
        legend.get_style_context().add_class("dim-label")
        self.pack_start(legend, False, False, 0)

        # Canvas inside a scrolled window so wide layouts can scroll if the
        # window is shrunk below content size. propagate_natural_size lets the
        # window auto-fit small layouts (e.g. an 8-LED mouse) without forcing
        # an oversized minimum.
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_propagate_natural_width(True)
        scroll.set_propagate_natural_height(True)
        # Inset frame around the keyboard so it reads as a distinct panel
        # rather than floating flat against the dialog background.
        scroll.set_shadow_type(Gtk.ShadowType.IN)
        self._canvas = KeyboardCanvas()
        self._canvas.connect(GtkSignal.PAINT.value, self._on_canvas_paint)
        scroll.add(self._canvas)
        self.pack_start(scroll, True, True, 0)

        self._canvas.set_active_color(self._palette.get_color())
        if self._gradient_swatch is not None:
            self._canvas.set_gradient_colors_source(self._gradient_swatch.get_colors)
        try:
            base = sink.zone_base_color()
        except Exception as e:
            logger.debug("zone_base_color read failed: %s", e)
            base = None
        self._canvas.set_zone_base_color(base)
        self._refresh_layout()
        self._sync_from_sink()
        self._unsubscribe = sink.subscribe(self._on_sink_update)

    def shutdown(self) -> None:
        if self._unsubscribe:
            try:
                self._unsubscribe()
            except Exception as e:
                logger.debug("perkey sink unsubscribe failed: %s", e)
            self._unsubscribe = None
        try:
            self._palette.shutdown()
        except Exception as e:
            logger.debug("palette shutdown failed: %s", e)

    def _refresh_layout(self) -> None:
        if self._layout is None:
            # No registered layout: lay out all reported zones as a flat strip.
            from .layout import Cell

            zones = list(self._sink.zones)
            cells = tuple(Cell(zone_id=z, row=0, col=i, group="strip", label=self._sink.label(z)) for i, z in enumerate(zones))
            self._layout = Layout(cells=cells, rows=1, cols=max(1, len(zones)), description=f"flat strip ({len(zones)} zones)")
        bound = binding.bind(
            self._layout,
            list(self._sink.zones),
            self._sink.label,
        )
        self._canvas.set_layout(bound)

    def _sync_from_sink(self) -> None:
        self._canvas.set_colors(dict(self._sink.current))

    def _on_sink_update(self, current: dict[int, int]) -> None:
        self._canvas.set_colors(dict(current))

    def _on_color_changed(self, _palette, color: int) -> None:
        self._canvas.set_active_color(color)
        # Gradient swatch tracks only real picker colors; toggling unset
        # leaves it alone so the gradient setup isn't disturbed.
        picker = self._palette.get_picker_color()
        if self._gradient_swatch is not None:
            self._gradient_swatch.update(picker, self._palette.get_last_color())
        try:
            self._sink.set_palette_state(picker, self._palette.get_last_color())
        except Exception as e:
            logger.debug("set_palette_state failed: %s", e)

    def _on_tool_toggled(self, btn: Gtk.RadioButton, name: str) -> None:
        if btn.get_active():
            self._canvas.set_tool(name)

    def _on_fill_all(self, _btn) -> None:
        zones = self._canvas.bound_zone_ids()
        if not zones:
            return
        color = self._palette.get_picker_color()  # always a real RGB, ignores the unset toggle
        delta = {z: color for z in zones}
        self._canvas.update_colors(delta)
        self._sink.write_bulk(delta)

    def _on_clear_all(self, _btn) -> None:
        zones = self._canvas.bound_zone_ids()
        if not zones:
            return
        delta = {z: UNSET_COLOR for z in zones}
        self._canvas.update_colors(delta)
        self._sink.write_bulk(delta)

    def _on_canvas_paint(self, _canvas, delta: dict) -> None:
        if not delta:
            return
        if len(delta) == 1:
            zone, color = next(iter(delta.items()))
            self._sink.write_one(int(zone), int(color))
        else:
            self._sink.write_bulk({int(z): int(c) for z, c in delta.items()})

    def _on_macros(self, _btn) -> None:
        window = self.get_toplevel()
        if not isinstance(window, Gtk.Window):
            window = None
        dlg = MacroEditor(window, self._device, gkeys=["G1", "G2", "G3", "G4", "G5"])
        dlg.show_all()
        response = dlg.run()
        if response == Gtk.ResponseType.OK:
            dlg.apply()
        dlg.destroy()
