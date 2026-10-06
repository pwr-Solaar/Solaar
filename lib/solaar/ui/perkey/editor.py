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

"""Editor widget: toolbar + canvas + right-hand colour sidebar.

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
from .palette import UNSET_COLOR  # NOQA: E402
from .palette import GradientSwatch  # NOQA: E402
from .palette import Palette  # NOQA: E402
from .palette import _int_to_rgba  # NOQA: E402
from .palette import _rgb_to_int  # NOQA: E402
from .protocol import PerKeyColorSink  # NOQA: E402

logger = logging.getLogger(__name__)


class GtkSignal(Enum):
    CLICKED = "clicked"
    COLOR_CHANGED = "color-changed"
    EDIT_COLOR = "edit-color"
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
        fill_all.set_tooltip_text(
            _("Paint every key on the layout with the current colour. " "Individual keys can then be overridden.")
        )
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
        self._palette = Palette(
            active=initial_active,
            previous=initial_previous,
            orientation=Gtk.Orientation.VERTICAL,
        )
        self._palette.connect(GtkSignal.COLOR_CHANGED.value, self._on_color_changed)
        self._palette.connect(GtkSignal.EDIT_COLOR.value, self._on_edit_color)
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

        # Colour sidebar: the active-colour picker, preset swatches and the
        # colours currently used on the keys live in a vertical strip to the
        # right of the canvas so they stay within easy reach while painting,
        # instead of hiding at the end of the top toolbar.
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        body.pack_start(scroll, True, True, 0)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sidebar.set_valign(Gtk.Align.START)
        sidebar.pack_start(self._palette, False, False, 0)
        sidebar.pack_start(self._build_profiles_section(), False, False, 0)
        body.pack_start(sidebar, False, False, 0)

        self.pack_start(body, True, True, 0)

        self._refresh_profiles()

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
        self._refresh_used_colors()

    def _on_sink_update(self, current: dict[int, int]) -> None:
        self._canvas.set_colors(dict(current))
        self._refresh_used_colors()

    def _refresh_used_colors(self) -> None:
        try:
            colors = [c for c in (self._sink.current or {}).values()]
        except Exception as e:
            logger.debug("used colors read failed: %s", e)
            colors = []
        self._palette.set_used_colors(colors)

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

    def _on_edit_color(self, _palette, from_color: int) -> None:
        """Double-click a used colour: open the custom colour editor with that
        colour loaded. On Select/OK, replace that colour on every key showing
        it and update the used-colour slot in place to the new colour.
        """
        try:
            current = dict(self._sink.current)
        except Exception as e:
            logger.debug("edit-color current read failed: %s", e)
            return
        from_color = int(from_color)
        if from_color < 0:
            return
        zones = [z for z, c in current.items() if isinstance(c, int) and c >= 0 and int(c) == from_color]
        if not zones:
            return
        window = self.get_toplevel()
        if not isinstance(window, Gtk.Window):
            window = None
        # The custom colour editor (colour wheel + tone sliders), not the
        # palette-picker tab.
        dialog = Gtk.ColorSelectionDialog(title=_("Edit colour"), transient_for=window)
        dialog.get_color_selection().set_has_opacity_control(False)
        dialog.get_color_selection().set_current_rgba(_int_to_rgba(from_color))

        def _apply(to_color: int) -> None:
            delta = {z: int(to_color) for z in zones}
            self._canvas.update_colors(delta)
            try:
                self._sink.write_bulk(delta)
            except Exception as e:
                logger.debug("edit-color write failed: %s", e)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            to_color = _rgb_to_int(dialog.get_color_selection().get_current_rgba())
            # Update the used-colour slot in place before the sink notify
            # reconciles the row, so the new colour keeps this slot's position.
            self._palette.replace_used_color(from_color, to_color)
            _apply(to_color)
        dialog.destroy()

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

    # ---- profiles (save / apply per-device lighting snapshots locally) ----

    def _build_profiles_section(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        title = Gtk.Label(label=_("Profiles"))
        title.set_xalign(0.0)
        title.get_style_context().add_class("dim-label")
        box.pack_start(title, False, False, 0)

        # Name + Save
        self._profile_name = Gtk.Entry()
        self._profile_name.set_placeholder_text(_("Profile name"))
        save_btn = Gtk.Button(label=_("Save"))
        save_btn.connect(GtkSignal.CLICKED.value, self._on_save_profile)
        name_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_row.pack_start(self._profile_name, True, True, 0)
        name_row.pack_start(save_btn, False, False, 0)
        box.pack_start(name_row, False, False, 0)

        # Pick + Apply / Delete
        self._profile_combo = Gtk.ComboBoxText()
        self._profile_combo.set_hexpand(True)
        apply_btn = Gtk.Button(label=_("Apply"))
        apply_btn.connect(GtkSignal.CLICKED.value, self._on_apply_profile)
        del_btn = Gtk.Button(label=_("Delete"))
        del_btn.connect(GtkSignal.CLICKED.value, self._on_delete_profile)
        load_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        load_row.pack_start(self._profile_combo, True, True, 0)
        load_row.pack_start(apply_btn, False, False, 0)
        load_row.pack_start(del_btn, False, False, 0)
        box.pack_start(load_row, False, False, 0)

        # Copy a lighting profile saved on another keyboard (e.g. G815 -> G915).
        copy_btn = Gtk.Button(label=_("Copy from another keyboard…"))
        copy_btn.set_tooltip_text(
            _("Bring in a per-key lighting profile saved on another keyboard. Keys are "
              "remapped by position, so it works between full/TKL and ANSI/ISO boards.")
        )
        copy_btn.connect(GtkSignal.CLICKED.value, self._on_copy_from_other)
        copy_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        copy_row.pack_start(copy_btn, True, True, 0)
        box.pack_start(copy_row, False, False, 0)

        self._active_profile_label = Gtk.Label(label="")
        self._active_profile_label.set_xalign(0.0)
        self._active_profile_label.get_style_context().add_class("dim-label")
        box.pack_start(self._active_profile_label, False, False, 0)
        return box

    def _refresh_profiles(self) -> None:
        try:
            profiles = self._sink.profiles()
            active = self._sink.active_profile()
        except Exception as e:
            logger.debug("profiles read failed: %s", e)
            profiles = {}
            active = None
        combo = self._profile_combo
        prior = combo.get_active_text()
        combo.remove_all()
        names = sorted(profiles.keys())
        for n in names:
            combo.append_text(n)
        if names:
            target = prior if prior in names else (active if active in names else names[0])
            combo.set_active(names.index(target))
        else:
            combo.set_active(-1)
        self._active_profile_label.set_text(_("Active: {name}").format(name=active) if active else "")

    def _on_save_profile(self, _btn) -> None:
        name = (self._profile_name.get_text() or "").strip()
        if not name:
            return
        try:
            current = dict(self._sink.current)
        except Exception as e:
            logger.debug("save profile current read failed: %s", e)
            return
        try:
            self._sink.save_profile(name, current)
            self._sink.set_active_profile(name)
        except Exception as e:
            logger.debug("save_profile failed: %s", e)
            return
        self._refresh_profiles()

    def _on_apply_profile(self, _btn) -> None:
        name = self._profile_combo.get_active_text()
        if not name:
            return
        try:
            profiles = self._sink.profiles()
            colors = profiles.get(name)
            if not colors:
                return
            self._canvas.update_colors(dict(colors))
            self._sink.write_bulk(dict(colors))
            self._sink.set_active_profile(name)
        except Exception as e:
            logger.debug("apply profile failed: %s", e)
            return
        self._refresh_profiles()

    def _on_delete_profile(self, _btn) -> None:
        name = self._profile_combo.get_active_text()
        if not name:
            return
        try:
            self._sink.delete_profile(name)
        except Exception as e:
            logger.debug("delete profile failed: %s", e)
            return
        self._refresh_profiles()

    # ---- copy a lighting profile saved on another keyboard ----

    def _source_candidates(self) -> list:
        """Other keyboards that have saved per-key lighting profiles, read from
        the shared Solaar config (no need to open the other device). Returns a
        list of {'name', 'wpid', 'profiles'} dicts, excluding this device."""
        try:
            import solaar.configuration as configuration
        except Exception as e:
            logger.debug("copy: config import failed: %s", e)
            return []
        current_name = getattr(self._device, "name", None)
        result = []
        for entry in configuration._config[1:]:
            if not isinstance(entry, dict):
                continue
            name = entry.get("_NAME") or entry.get("_name")
            if not name or name == current_name:
                continue
            raw = entry.get("_profiles:per-key-lighting")
            if not isinstance(raw, dict) or not raw:
                continue
            profiles = {}
            for pname, colormap in raw.items():
                if isinstance(colormap, dict):
                    profiles[str(pname)] = {int(z): int(c) for z, c in colormap.items()}
            if profiles:
                result.append({"name": str(name), "wpid": entry.get("_wpid"), "profiles": profiles})
        return result

    def _source_layout(self, src_name: str, src_wpid, zones) -> Layout | None:
        """Best-effort reconstruction of the source keyboard's layout so we can
        remap keys by physical position. Zone country code isn't preserved in
        the config, so ISO boards fall back to an ANSI shape — acceptable for
        the alpha/numpad region and noted for future work."""
        from .layouts import layout_for

        hint = {
            "kind": "keyboard",
            "wpid": src_wpid,
            "codename": src_name,
            "name": src_name,
            "keyboard_layout": None,
            "zones": list(zones),
            "zone_count": len(zones),
        }
        return layout_for(0x8081, hint)

    def _remap_colors(self, src_colors: dict, src_name: str, src_wpid) -> dict:
        """Map a source keyboard's zone->colour buffer into this keyboard's
        zone space by physical (group, row, col) position. When the two boards
        share a layout this is effectively an identity copy. Zones the layout
        doesn't place (e.g. top-row media keys, or phantom slots) fall back to
        numeric-id preservation when the target device actually reports them,
        and are dropped otherwise."""
        target = self._layout
        if target is None:
            return dict(src_colors)
        # Device-reported zones — the canonical set the target can accept.
        try:
            target_zones = set(self._sink.zones)
        except Exception as e:
            logger.debug("copy: target zones read failed: %s", e)
            target_zones = set(target.by_zone())
        t_pos = {(c.group, c.row, c.col): c.zone_id for c in target.cells}
        src = self._source_layout(src_name, src_wpid, list(src_colors))
        if src is None:
            return {z: c for z, c in src_colors.items() if z in target_zones}
        s_by_zone = src.by_zone()
        out = {}
        for z, color in src_colors.items():
            cell = s_by_zone.get(z)
            tz = t_pos.get((cell.group, cell.row, cell.col)) if cell is not None else None
            if tz is not None and tz != z:
                out[tz] = color
            elif z in target_zones:
                out[z] = color
        return out

    def _on_copy_from_other(self, _btn) -> None:
        candidates = self._source_candidates()
        window = self.get_toplevel() if isinstance(self.get_toplevel(), Gtk.Window) else None
        dialog = Gtk.Dialog(
            title=_("Copy profile from another keyboard"),
            transient_for=window,
            modal=True,
            buttons=(_("Cancel"), Gtk.ResponseType.CANCEL, _("Copy"), Gtk.ResponseType.OK),
        )
        dialog.set_default_response(Gtk.ResponseType.OK)
        area = dialog.get_content_area()
        area.set_spacing(8)
        area.set_margin_top(8)
        area.set_margin_bottom(8)
        area.set_margin_start(8)
        area.set_margin_end(8)

        if not candidates:
            lbl = Gtk.Label(
                label=_(
                    "No other keyboards with saved per-key lighting profiles were found.\n"
                    "Open the per-key editor on the source keyboard and save a profile there first."
                )
            )
            lbl.set_xalign(0.0)
            area.pack_start(lbl, False, False, 0)
            dialog.get_widget_for_response(Gtk.ResponseType.OK).set_sensitive(False)
            dialog.show_all()
            dialog.run()
            dialog.destroy()
            return

        # Flatten devices x profiles into one picker list: "DeviceName · Profile".
        options = []
        for cand in candidates:
            for pname in sorted(cand["profiles"]):
                options.append((cand, pname))

        combo = Gtk.ComboBoxText()
        for cand, pname in options:
            combo.append_text(f"{cand['name']} \u00b7 {pname}")
        combo.set_active(0)

        entry = Gtk.Entry()
        first_cand, first_pname = options[0]
        entry.set_text(f"{first_pname} (from {first_cand['name']})")

        def _on_source_changed(*_a):
            cand, pname = options[max(0, combo.get_active())]
            entry.set_text(f"{pname} (from {cand['name']})")

        combo.connect(GtkSignal.CHANGED.value, _on_source_changed)

        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        l1 = Gtk.Label(label=_("Source profile:"))
        l1.set_xalign(0.0)
        row1.pack_start(l1, False, False, 0)
        row1.pack_start(combo, True, True, 0)
        row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        l2 = Gtk.Label(label=_("Save as:"))
        l2.set_xalign(0.0)
        row2.pack_start(l2, False, False, 0)
        row2.pack_start(entry, True, True, 0)
        area.pack_start(row1, False, False, 0)
        area.pack_start(row2, False, False, 0)

        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            cand, pname = options[max(0, combo.get_active())]
            target_name = (entry.get_text() or "").strip() or pname
            try:
                src_colors = dict(cand["profiles"][pname])
            except Exception as e:
                logger.debug("copy: profile read failed: %s", e)
                dialog.destroy()
                return
            colors = self._remap_colors(src_colors, cand["name"], cand["wpid"])
            try:
                self._sink.save_profile(target_name, colors)
                self._canvas.update_colors(dict(colors))
                self._sink.write_bulk(dict(colors))
                self._sink.set_active_profile(target_name)
            except Exception as e:
                logger.debug("copy: apply failed: %s", e)
            self._refresh_profiles()
        dialog.destroy()

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
