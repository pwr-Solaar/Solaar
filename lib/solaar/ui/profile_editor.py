## Copyright (C) 2026  Solaar Contributors
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

"""Onboard Profile Editor GUI for Solaar.

Provides:
- OnboardProfilesControl: an inline control embedded in Solaar's settings panel
  replacing ChoiceControl for the onboard_profiles setting. It features a profile
  selector dropdown plus an 'Edit Profiles…' button.
- OnboardProfileEditorDialog: an interactive editor dialog allowing the user to view, edit,
  copy, save, and reload onboard profiles (DPI levels/stages, report rate, default/shift DPI,
  and profile enable flags) directly in the mouse hardware's flash memory.
"""

from __future__ import annotations

import logging
import threading
from typing import Hashable

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # NOQA: E402
import yaml  # NOQA: E402

from logitech_receiver import common  # NOQA: E402
from logitech_receiver import hidpp20  # NOQA: E402
from logitech_receiver import settings_templates  # NOQA: E402
from solaar.i18n import _  # NOQA: E402

logger = logging.getLogger(__name__)

# Registry of open dialogs keyed by stable per-device identifier
_dialogs: dict[Hashable, OnboardProfileEditorDialog] = {}


def _is_onboard_disabled(val) -> bool:
    """Safe check whether onboard profile value represents Disabled / Host mode."""
    if val is None:
        return True
    if isinstance(val, bytes):
        return val in (b"\x00\x00", b"\x00", b"")
    if isinstance(val, (int, common.NamedInt)):
        return int(val) == 0
    if isinstance(val, str):
        return val.lower() in ("disabled", "0")
    return False


def _device_key(device) -> Hashable:
    """Stable key to identify a physical device across transports."""
    return (
        getattr(device, "unitId", None)
        or getattr(device, "serial", None)
        or getattr(device, "hid_serial", None)
        or getattr(device, "codename", None)
        or id(device)
    )


def notify_dpi_changed(device, value) -> None:
    """Notify open profile dialog that active DPI stage has changed on device."""
    key = _device_key(device)
    dlg = _dialogs.get(key)
    if dlg and dlg._window is not None:
        GLib.idle_add(dlg.update_active_dpi_from_value, value)


def get_profile_dialog(device, parent_window=None, sbox=None) -> OnboardProfileEditorDialog:
    """Get or create the profile editor dialog for a device."""
    key = _device_key(device)
    dlg = _dialogs.get(key)
    if dlg is None:
        dlg = OnboardProfileEditorDialog(key, device, parent_window=parent_window, sbox=sbox)
        _dialogs[key] = dlg
    else:
        if parent_window:
            dlg.parent_window = parent_window
            if dlg._window is not None:
                dlg._window.set_transient_for(parent_window)
        if sbox:
            dlg.sbox = sbox
    return dlg


def _get_dpi_range(device) -> tuple[int, int, int]:
    """Retrieve min DPI, max DPI, and step for device sensor."""
    dpi_setting = next((s for s in getattr(device, "settings", []) or [] if s.name in ("dpi", "dpi_extended")), None)
    if dpi_setting and hasattr(dpi_setting, "choices"):
        c = dpi_setting.choices
        if isinstance(c, dict) and 0 in c:
            try:
                vals = [int(x) for x in c[0] if x is not None]
                if len(vals) > 1:
                    step = abs(vals[1] - vals[0])
                    return min(vals), max(vals), max(1, step)
                elif len(vals) == 1:
                    return vals[0], vals[0], 50
            except (ValueError, TypeError):
                pass
        elif hasattr(c, "__iter__"):
            try:
                vals = [int(x) for x in c if x is not None]
                if len(vals) > 1:
                    step = abs(vals[1] - vals[0])
                    return min(vals), max(vals), max(1, step)
                elif len(vals) == 1:
                    return vals[0], vals[0], 50
            except (ValueError, TypeError):
                pass
    return 100, 25600, 50


def _get_report_rate_choices(profile_version: int | None) -> list[tuple[int, str]]:
    """Return (value, label) pairs for report rate based on profile version."""
    if profile_version == 7:
        return [
            (3, _("1000 Hz (1 ms)")),
            (2, _("500 Hz (2 ms)")),
            (1, _("250 Hz (4 ms)")),
            (0, _("125 Hz (8 ms)")),
        ]
    else:
        return [
            (1, _("1000 Hz (1 ms)")),
            (2, _("500 Hz (2 ms)")),
            (4, _("250 Hz (4 ms)")),
            (8, _("125 Hz (8 ms)")),
        ]


# ---------------------------------------------------------------------------
# Inline Setting Control for Solaar's Configuration Panel
# ---------------------------------------------------------------------------
class OnboardProfilesControl(Gtk.Box):
    """Custom control replacing ChoiceControlLittle for OnboardProfiles.

    Renders a profile selector dropdown and an 'Edit Profiles…' button.
    """

    def __init__(self, sbox) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.sbox = sbox
        self._setting = sbox.setting
        self.choices = getattr(sbox.setting, "choices", None) or []

        self.combo_box = Gtk.ComboBoxText(halign=Gtk.Align.FILL)
        self.set_choices(self.choices)
        self.combo_box.connect("changed", self._on_combo_changed)
        self.pack_start(self.combo_box, False, False, 0)

        self.edit_btn = Gtk.Button.new_with_label(_("Edit Profiles…"))
        self.edit_btn.set_tooltip_text(_("View and edit onboard profile DPI levels and settings in mouse memory"))
        self.edit_btn.connect("clicked", self._on_edit_clicked)
        self.pack_start(self.edit_btn, False, False, 0)

    # ---- Control protocol ----

    def set_choices(self, choices) -> None:
        self.choices = choices if choices is not None else []
        self.combo_box.remove_all()
        for choice in self.choices:
            self.combo_box.append(str(int(choice)), _(str(choice)))

    def get_value(self) -> int | None:
        active_id = self.combo_box.get_active_id()
        if active_id is None:
            return None
        val_int = int(active_id)
        for c in self.choices:
            if int(c) == val_int:
                return c
        return val_int

    def set_value(self, value) -> None:
        if value is None:
            return
        if isinstance(value, bytes):
            value = common.bytes2int(value)
        self.combo_box.set_active_id(str(int(value)))

    def set_sensitive(self, sensitive: bool) -> None:
        self.combo_box.set_sensitive(bool(sensitive))
        device = getattr(self._setting, "_device", None)
        is_online = getattr(device, "online", True) if device else True
        self.edit_btn.set_sensitive(bool(is_online))

    def layout(self, sbox, label, change, spinner, failed):
        sbox.pack_start(label, False, False, 0)
        sbox.pack_end(change, False, False, 0)
        sbox.pack_end(self, False, False, 0)
        sbox.pack_end(spinner, False, False, 0)
        sbox.pack_end(failed, False, False, 0)
        return self

    # ---- Event handlers ----

    def _on_combo_changed(self, *_args) -> None:
        if self.combo_box.get_sensitive():
            val = self.get_value()
            if val is not None and getattr(self._setting, "_value", None) != val:
                from solaar.ui.config_panel import _write_async

                _write_async(self._setting, val, self.sbox)

    def _on_edit_clicked(self, _btn) -> None:
        device = getattr(self._setting, "_device", None)
        if not device:
            return
        toplevel = self.get_toplevel()
        parent_window = toplevel if isinstance(toplevel, Gtk.Window) else None
        dlg = get_profile_dialog(device, parent_window=parent_window, sbox=self.sbox)
        dlg.present()


# ---------------------------------------------------------------------------
# Onboard Profile Editor Dialog Window
# ---------------------------------------------------------------------------
class OnboardProfileEditorDialog:
    """Dialog allowing the user to view, edit, copy, and save onboard profiles."""

    def __init__(self, key: Hashable, device, parent_window=None, sbox=None) -> None:
        self._key = key
        self.device = device
        self.parent_window = parent_window
        self.sbox = sbox
        self._window: Gtk.Window | None = None
        self._profiles = getattr(device, "profiles", None)
        self._selected_idx = 1
        self._separate_xy = False
        self._loading = False
        self._stage_widgets: list[dict] = []
        self._default_radio_group = None
        self._shift_radio_group = None

        self._min_dpi, self._max_dpi, self._step_dpi = _get_dpi_range(device)

    def _on_delete(self, _w, _e) -> bool:
        self._destroy()
        _dialogs.pop(self._key, None)
        return True

    def _destroy(self) -> None:
        if self._window is not None:
            self._window.destroy()
            self._window = None

    def present(self) -> None:
        if self._window is not None:
            self._window.present()
            return

        self._window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        if self.parent_window:
            self._window.set_transient_for(self.parent_window)
        self._window.set_title(_("Onboard Profiles") + f" — {self.device.name}")
        self._window.set_default_size(600, 620)
        self._window.set_border_width(12)
        self._window.connect("delete-event", self._on_delete)
        self._window.connect("destroy", lambda _w: _dialogs.pop(self._key, None))

        # Main wrapper box
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._window.add(vbox)

        # 1. InfoBar for user notifications / alerts
        self._infobar = Gtk.InfoBar()
        self._infobar_label = Gtk.Label()
        self._infobar_label.set_line_wrap(True)
        self._infobar_label.set_xalign(0.0)
        self._infobar_label.show()
        self._infobar.get_content_area().add(self._infobar_label)
        self._infobar.set_show_close_button(True)
        self._infobar.connect("response", lambda ib, _r: ib.hide())
        self._infobar.set_no_show_all(True)
        vbox.pack_start(self._infobar, False, False, 0)

        # 2. Header Box: device icon + title + mode status
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon = Gtk.Image.new_from_icon_name("input-mouse", Gtk.IconSize.DND)
        header_box.pack_start(icon, False, False, 0)

        info_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_lbl = Gtk.Label()
        title_lbl.set_markup(f"<big><b>{self.device.name}</b></big>")
        title_lbl.set_xalign(0.0)
        info_vbox.pack_start(title_lbl, False, False, 0)

        self._status_lbl = Gtk.Label()
        self._status_lbl.set_xalign(0.0)
        info_vbox.pack_start(self._status_lbl, False, False, 0)
        header_box.pack_start(info_vbox, True, True, 0)
        vbox.pack_start(header_box, False, False, 0)

        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)

        # 3. Profile selection row
        sel_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        sel_lbl = Gtk.Label(label=_("Profile:"))
        sel_box.pack_start(sel_lbl, False, False, 0)

        self._profile_combo = Gtk.ComboBoxText()
        self._profile_combo.connect("changed", self._on_profile_selection_changed)
        sel_box.pack_start(self._profile_combo, False, False, 0)

        self._enabled_chk = Gtk.CheckButton(label=_("Enabled on Mouse"))
        self._enabled_chk.set_tooltip_text(_("When enabled, this profile is selectable and cycled in mouse memory"))
        self._enabled_chk.connect("toggled", self._on_enabled_toggled)
        sel_box.pack_start(self._enabled_chk, False, False, 6)

        # Profile management helpers: Copy from & Reset
        self._copy_btn = Gtk.Button.new_with_label(_("Copy from…"))
        self._copy_btn.set_tooltip_text(_("Copy DPI stages and settings from another profile to this profile"))
        self._copy_btn.connect("clicked", self._on_copy_from_clicked)
        sel_box.pack_start(self._copy_btn, False, False, 0)

        self._reset_btn = Gtk.Button.new_with_label(_("Reset"))
        self._reset_btn.set_tooltip_text(_("Reset this profile to default DPI stages and report rate"))
        self._reset_btn.connect("clicked", self._on_reset_defaults_clicked)
        sel_box.pack_start(self._reset_btn, False, False, 0)

        self._activate_btn = Gtk.Button.new_with_label(_("Activate Profile"))
        self._activate_btn.set_tooltip_text(_("Set this profile as the currently active profile on the mouse"))
        self._activate_btn.connect("clicked", self._on_activate_clicked)
        sel_box.pack_end(self._activate_btn, False, False, 0)
        vbox.pack_start(sel_box, False, False, 0)

        # 4. Scrollable Content Area: DPI Stages & Settings
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        content_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        scrolled.add(content_vbox)
        vbox.pack_start(scrolled, True, True, 0)

        # Section: DPI Stages
        dpi_frame = Gtk.Frame(label=_("DPI Stages (Sensitivity)"))
        dpi_frame_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        dpi_frame_box.set_border_width(10)
        dpi_frame.add(dpi_frame_box)
        content_vbox.pack_start(dpi_frame, False, False, 0)

        dpi_desc = Gtk.Label()
        dpi_desc.set_markup(
            f"<small>{_('Configure the 5 DPI stages cycled by the mouse physical DPI button.')}</small>"
        )
        dpi_desc.set_xalign(0.0)
        dpi_frame_box.pack_start(dpi_desc, False, False, 0)

        # Grid of stages
        self._grid = Gtk.Grid()
        self._grid.set_column_spacing(10)
        self._grid.set_row_spacing(8)
        dpi_frame_box.pack_start(self._grid, False, False, 0)

        # Headers for Default & Shift radio columns
        hdr_stage = Gtk.Label(label=_("Stage"))
        hdr_stage.set_xalign(0.0)
        self._grid.attach(hdr_stage, 0, 0, 1, 1)

        hdr_dpi = Gtk.Label(label=_("DPI"))
        hdr_dpi.set_xalign(0.0)
        self._grid.attach(hdr_dpi, 1, 0, 1, 1)

        hdr_slider = Gtk.Label(label=_("Quick Adjustment"))
        hdr_slider.set_xalign(0.0)
        self._grid.attach(hdr_slider, 2, 0, 1, 1)

        hdr_def = Gtk.Label(label=_("Default"))
        self._grid.attach(hdr_def, 3, 0, 1, 1)

        hdr_shift = Gtk.Label(label=_("Shift"))
        self._grid.attach(hdr_shift, 4, 0, 1, 1)

        self._build_stage_rows()

        # Separate X/Y DPI checkbutton
        self._sep_xy_chk = Gtk.CheckButton(label=_("Separate X and Y DPI"))
        self._sep_xy_chk.set_tooltip_text(_("Configure independent horizontal (X) and vertical (Y) sensitivities"))
        self._sep_xy_chk.connect("toggled", self._on_separate_xy_toggled)
        dpi_frame_box.pack_start(self._sep_xy_chk, False, False, 0)

        # Section: Report Rate
        rr_frame = Gtk.Frame(label=_("Report Rate & Polling"))
        rr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        rr_box.set_border_width(10)
        rr_frame.add(rr_box)
        content_vbox.pack_start(rr_frame, False, False, 0)

        rr_lbl = Gtk.Label(label=_("Report Rate:"))
        rr_box.pack_start(rr_lbl, False, False, 0)

        self._rr_combo = Gtk.ComboBoxText()
        self._rr_combo.connect("changed", self._on_report_rate_changed)
        rr_box.pack_start(self._rr_combo, False, False, 0)

        # Advanced: Sleep Timeouts Expander
        self._adv_expander = Gtk.Expander(label=_("Advanced: Sleep Timeouts"))
        adv_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        adv_box.set_border_width(8)
        self._adv_expander.add(adv_box)

        adv_box.pack_start(Gtk.Label(label=_("Power Save (s):")), False, False, 0)
        self._ps_timeout_spin = Gtk.SpinButton.new_with_range(10, 600, 10)
        self._ps_timeout_spin.connect("value-changed", self._on_timeout_changed)
        adv_box.pack_start(self._ps_timeout_spin, False, False, 0)

        adv_box.pack_start(Gtk.Label(label=_("Power Off (s):")), False, False, 0)
        self._po_timeout_spin = Gtk.SpinButton.new_with_range(60, 3600, 60)
        self._po_timeout_spin.connect("value-changed", self._on_timeout_changed)
        adv_box.pack_start(self._po_timeout_spin, False, False, 0)

        content_vbox.pack_start(self._adv_expander, False, False, 0)

        # 5. Action Buttons Bar
        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        vbox.pack_end(btn_box, False, False, 0)

        # Left action buttons: Import / Export YAML
        self._import_btn = Gtk.Button.new_with_label(_("Import YAML…"))
        self._import_btn.set_tooltip_text(_("Load profile settings from a YAML file"))
        self._import_btn.connect("clicked", self._on_import_yaml)
        btn_box.pack_start(self._import_btn, False, False, 0)

        self._export_btn = Gtk.Button.new_with_label(_("Export YAML…"))
        self._export_btn.set_tooltip_text(_("Export profile settings to a YAML file"))
        self._export_btn.connect("clicked", self._on_export_yaml)
        btn_box.pack_start(self._export_btn, False, False, 0)

        # Right action buttons: Reload / Save / Close
        self._close_btn = Gtk.Button.new_with_label(_("Close"))
        self._close_btn.connect("clicked", lambda _b: self._window.close())
        btn_box.pack_end(self._close_btn, False, False, 0)

        self._save_btn = Gtk.Button.new_with_label(_("Save to Mouse"))
        self._save_btn.get_style_context().add_class(Gtk.STYLE_CLASS_SUGGESTED_ACTION)
        self._save_btn.set_tooltip_text(_("Write modified profile sectors to mouse internal memory"))
        self._save_btn.connect("clicked", self._on_save_clicked)
        btn_box.pack_end(self._save_btn, False, False, 0)

        self._reload_btn = Gtk.Button.new_with_label(_("Reload from Mouse"))
        self._reload_btn.set_tooltip_text(_("Discard changes and re-read profiles from mouse memory"))
        self._reload_btn.connect("clicked", self._on_reload_clicked)
        btn_box.pack_end(self._reload_btn, False, False, 0)

        self._save_spinner = Gtk.Spinner()
        btn_box.pack_end(self._save_spinner, False, False, 4)

        # Populate and show
        self._refresh_all()
        self._window.show_all()
        self._infobar.hide()
        self._save_spinner.hide()

    def _build_stage_rows(self) -> None:
        """Create the 5 DPI stage rows in the grid."""
        self._stage_widgets.clear()
        self._default_radio_group = None
        self._shift_radio_group = None

        for i in range(5):
            row_idx = i + 1

            # Stage label + active badge
            stage_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            stage_lbl = Gtk.Label()
            stage_lbl.set_markup(f"<b>{_('Stage')} {i + 1}</b>")
            stage_box.pack_start(stage_lbl, False, False, 0)

            active_badge = Gtk.Label()
            active_badge.set_markup("<small><span foreground='#1b8a2c'><b>● Active</b></span></small>")
            stage_box.pack_start(active_badge, False, False, 0)
            active_badge.set_no_show_all(True)
            active_badge.hide()

            self._grid.attach(stage_box, 0, row_idx, 1, 1)

            # SpinButton for X DPI and optional Y DPI
            spin_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

            lbl_x = Gtk.Label(label="X:")
            lbl_x.set_no_show_all(True)
            lbl_x.hide()
            spin_box.pack_start(lbl_x, False, False, 0)

            spin_x = Gtk.SpinButton.new_with_range(self._min_dpi, self._max_dpi, self._step_dpi)
            spin_x.set_increments(self._step_dpi, self._step_dpi * 4)
            spin_x.set_digits(0)
            spin_x.set_snap_to_ticks(True)
            spin_box.pack_start(spin_x, False, False, 0)

            # SpinButton for Y DPI (initially hidden)
            lbl_y = Gtk.Label(label="Y:")
            lbl_y.set_no_show_all(True)
            lbl_y.hide()
            spin_box.pack_start(lbl_y, False, False, 0)

            spin_y = Gtk.SpinButton.new_with_range(self._min_dpi, self._max_dpi, self._step_dpi)
            spin_y.set_increments(self._step_dpi, self._step_dpi * 4)
            spin_y.set_digits(0)
            spin_y.set_snap_to_ticks(True)
            lbl_y.set_no_show_all(True)
            spin_y.set_no_show_all(True)
            lbl_y.hide()
            spin_y.hide()
            spin_box.pack_start(spin_y, False, False, 0)

            self._grid.attach(spin_box, 1, row_idx, 1, 1)

            # Slider for quick visual adjustment
            scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, self._min_dpi, self._max_dpi, self._step_dpi)
            scale.set_round_digits(0)
            scale.set_digits(0)
            scale.set_size_request(180, -1)
            scale.set_hexpand(True)
            self._grid.attach(scale, 2, row_idx, 1, 1)

            # Bind slider <-> spin_x
            def _on_spin_changed(spin, s=scale, idx=i):
                val = int(spin.get_value())
                if int(s.get_value()) != val:
                    s.set_value(val)
                self._on_dpi_stage_modified(idx)

            def _on_scale_changed(s, spin=spin_x, idx=i):
                val = int(s.get_value())
                if int(spin.get_value()) != val:
                    spin.set_value(val)
                self._on_dpi_stage_modified(idx)

            def _on_spin_y_changed(_spin, idx=i):
                self._on_dpi_stage_modified(idx)

            spin_x.connect("value-changed", _on_spin_changed)
            scale.connect("value-changed", _on_scale_changed)
            spin_y.connect("value-changed", _on_spin_y_changed)

            # Default Radio
            radio_def = Gtk.RadioButton.new_from_widget(self._default_radio_group)
            if self._default_radio_group is None:
                self._default_radio_group = radio_def
            radio_def.set_halign(Gtk.Align.CENTER)
            radio_def.connect("toggled", self._on_default_radio_toggled, i)
            self._grid.attach(radio_def, 3, row_idx, 1, 1)

            # Shift Radio
            radio_shift = Gtk.RadioButton.new_from_widget(self._shift_radio_group)
            if self._shift_radio_group is None:
                self._shift_radio_group = radio_shift
            radio_shift.set_halign(Gtk.Align.CENTER)
            radio_shift.connect("toggled", self._on_shift_radio_toggled, i)
            self._grid.attach(radio_shift, 4, row_idx, 1, 1)

            self._stage_widgets.append(
                {
                    "badge": active_badge,
                    "lbl_x": lbl_x,
                    "spin_x": spin_x,
                    "lbl_y": lbl_y,
                    "spin_y": spin_y,
                    "scale": scale,
                    "radio_def": radio_def,
                    "radio_shift": radio_shift,
                }
            )

    # ---- Live active stage update ----

    def update_active_dpi_from_value(self, value) -> None:
        """Update live active DPI stage badge from setting value."""
        onboard_setting = next((s for s in getattr(self.device, "settings", []) or [] if s.name == "onboard_profiles"), None)
        active_val = getattr(onboard_setting, "_value", None)
        if _is_onboard_disabled(active_val):
            for w in self._stage_widgets:
                w["badge"].hide()
            return

        is_current_active = False
        try:
            is_current_active = int(active_val) == self._selected_idx
        except (ValueError, TypeError):
            pass

        if not is_current_active:
            for w in self._stage_widgets:
                w["badge"].hide()
            return

        target_dpi = None
        if isinstance(value, dict):
            target_dpi = value.get(0)
        elif isinstance(value, (int, common.NamedInt)):
            target_dpi = int(value)

        for w in self._stage_widgets:
            if target_dpi is not None and int(w["spin_x"].get_value()) == target_dpi:
                w["badge"].show()
            else:
                w["badge"].hide()

    # ---- Data Binding & UI Refresh ----

    def _show_info(self, text: str, msg_type=Gtk.MessageType.INFO) -> None:
        self._infobar.set_message_type(msg_type)
        self._infobar_label.set_text(text)
        self._infobar_label.show()
        self._infobar.show()
        if msg_type == Gtk.MessageType.INFO:
            GLib.timeout_add_seconds(6, self._infobar.hide)

    def _refresh_all(self) -> None:
        """Full refresh of dialog data from device profiles."""
        if not self._profiles:
            try:
                self._profiles = self.device.profiles
            except Exception as e:
                logger.error("Error reading profiles from device: %s", e)

        if not self._profiles or not getattr(self._profiles, "profiles", None):
            self._show_info(_("Could not read onboard profiles from mouse."), Gtk.MessageType.WARNING)
            self._status_lbl.set_text(_("Profiles: Not available"))
            return

        # Update Header mode status
        onboard_setting = next((s for s in getattr(self.device, "settings", []) or [] if s.name == "onboard_profiles"), None)
        active_val = getattr(onboard_setting, "_value", None)
        if active_val is None and onboard_setting:
            active_val = onboard_setting.read()

        is_disabled = _is_onboard_disabled(active_val)

        prof_ver = getattr(self._profiles, "profile_version", None)
        ver_text = f"Format {prof_ver}" if prof_ver else ""
        if is_disabled:
            self._status_lbl.set_markup(
                f"<small>{ver_text} • <i>{_('Device Mode: Host (Live DPI controlled by Solaar)')}</i></small>"
            )
        else:
            act_num = int(active_val) if active_val is not None else 1
            self._status_lbl.set_markup(
                f"<small>{ver_text} • <b><span foreground='#1b8a2c'>{_('Device Mode: On-Board (Profile %d)') % act_num}</span></b></small>"
            )

        # Populate profile selector dropdown
        self._profile_combo.handler_block_by_func(self._on_profile_selection_changed)
        self._profile_combo.remove_all()
        for idx in sorted(self._profiles.profiles.keys()):
            p = self._profiles.profiles[idx]
            is_active_prof = not is_disabled and (int(active_val or 0) == idx)
            is_enabled = bool(getattr(p, "enabled", 0))
            if is_active_prof:
                tag = f" ({_('Active')})"
            elif is_enabled:
                tag = f" ({_('Enabled')})"
            else:
                tag = f" ({_('Disabled')})"
            label = f"{_('Profile')} {idx}{tag}"
            self._profile_combo.append(str(idx), label)

        if self._selected_idx not in self._profiles.profiles:
            self._selected_idx = next(iter(sorted(self._profiles.profiles.keys())), 1)

        self._profile_combo.set_active_id(str(self._selected_idx))
        self._profile_combo.handler_unblock_by_func(self._on_profile_selection_changed)

        # Populate Report Rate dropdown choices
        self._rr_combo.handler_block_by_func(self._on_report_rate_changed)
        self._rr_combo.remove_all()
        for val, lbl in _get_report_rate_choices(prof_ver):
            self._rr_combo.append(str(val), lbl)
        self._rr_combo.handler_unblock_by_func(self._on_report_rate_changed)

        # Load currently selected profile
        self._load_profile(self._selected_idx)

    def _load_profile(self, profile_idx: int) -> None:
        """Load values of profile_idx into UI widgets."""
        if not self._profiles or profile_idx not in self._profiles.profiles:
            return

        self._loading = True
        try:
            p = self._profiles.profiles[profile_idx]

            # Enabled checkbutton
            self._enabled_chk.handler_block_by_func(self._on_enabled_toggled)
            self._enabled_chk.set_active(bool(getattr(p, "enabled", 0)))
            self._enabled_chk.handler_unblock_by_func(self._on_enabled_toggled)

            # Activate button status
            onboard_setting = next((s for s in getattr(self.device, "settings", []) or [] if s.name == "onboard_profiles"), None)
            active_val = getattr(onboard_setting, "_value", None)
            is_current_active = False
            if active_val is not None:
                try:
                    is_current_active = int(active_val) == profile_idx
                except (ValueError, TypeError):
                    pass

            is_valid_choice = False
            if onboard_setting and hasattr(onboard_setting, "choices") and onboard_setting.choices:
                is_valid_choice = any(int(c) == profile_idx for c in onboard_setting.choices)

            if is_current_active:
                self._activate_btn.set_sensitive(False)
                self._activate_btn.set_label(_("Current Active"))
                self._activate_btn.set_tooltip_text(_("This profile is currently active on the mouse"))
            elif not is_valid_choice:
                self._activate_btn.set_sensitive(False)
                self._activate_btn.set_label(_("Activate Profile"))
                self._activate_btn.set_tooltip_text(_("Enable and save this profile to mouse before activating it"))
            else:
                self._activate_btn.set_sensitive(True)
                self._activate_btn.set_label(_("Activate Profile"))
                self._activate_btn.set_tooltip_text(_("Set this profile as the currently active profile on the mouse"))

            # DPI Stages
            res_x = getattr(p, "resolutions_x", getattr(p, "resolutions", [800] * 5))
            if not res_x:
                res_x = [800] * 5
            res_y = getattr(p, "resolutions_y", res_x)
            if not res_y:
                res_y = res_x

            def_idx = getattr(p, "resolution_default_index", 0)
            if not (0 <= def_idx < 5):
                def_idx = 0
            shift_idx = getattr(p, "resolution_shift_index", 0)
            if not (0 <= shift_idx < 5):
                shift_idx = 0
            dpi_act_idx = getattr(p, "dpi_active_index", None)

            # Detect separate X/Y and update checkbox & widget visibility
            has_diff_xy = any(rx != ry for rx, ry in zip(res_x, res_y)) if len(res_x) == len(res_y) else False
            self._separate_xy = bool(has_diff_xy)

            self._sep_xy_chk.handler_block_by_func(self._on_separate_xy_toggled)
            self._sep_xy_chk.set_active(self._separate_xy)
            self._sep_xy_chk.handler_unblock_by_func(self._on_separate_xy_toggled)

            for i, w in enumerate(self._stage_widgets):
                val_x = res_x[i] if i < len(res_x) else 800
                val_y = res_y[i] if i < len(res_y) else val_x

                w["spin_x"].set_value(val_x)
                w["scale"].set_value(val_x)
                w["spin_y"].set_value(val_y)

                if self._separate_xy:
                    w["lbl_x"].show()
                    w["lbl_y"].show()
                    w["spin_y"].show()
                else:
                    w["lbl_x"].hide()
                    w["lbl_y"].hide()
                    w["spin_y"].hide()

                # Active stage indicator
                if is_current_active and dpi_act_idx == i:
                    w["badge"].show()
                else:
                    w["badge"].hide()

                # Default & shift radios
                w["radio_def"].handler_block_by_func(self._on_default_radio_toggled)
                w["radio_def"].set_active(i == def_idx)
                w["radio_def"].handler_unblock_by_func(self._on_default_radio_toggled)

                w["radio_shift"].handler_block_by_func(self._on_shift_radio_toggled)
                w["radio_shift"].set_active(i == shift_idx)
                w["radio_shift"].handler_unblock_by_func(self._on_shift_radio_toggled)

            # Report Rate
            self._rr_combo.handler_block_by_func(self._on_report_rate_changed)
            rr_val = getattr(p, "report_rate", 3)
            self._rr_combo.set_active_id(str(rr_val))
            self._rr_combo.handler_unblock_by_func(self._on_report_rate_changed)

            # Sleep Timeouts
            self._ps_timeout_spin.handler_block_by_func(self._on_timeout_changed)
            self._po_timeout_spin.handler_block_by_func(self._on_timeout_changed)
            self._ps_timeout_spin.set_value(getattr(p, "ps_timeout", 60) or 60)
            self._po_timeout_spin.set_value(getattr(p, "po_timeout", 300) or 300)
            self._ps_timeout_spin.handler_unblock_by_func(self._on_timeout_changed)
            self._po_timeout_spin.handler_unblock_by_func(self._on_timeout_changed)
        finally:
            self._loading = False

    def _sync_ui_to_profile(self, profile_idx: int) -> None:
        """Read UI widgets and apply to in-memory profile object."""
        if not self._profiles or profile_idx not in self._profiles.profiles:
            return

        p = self._profiles.profiles[profile_idx]
        p.enabled = 1 if self._enabled_chk.get_active() else 0

        res_x = []
        res_y = []
        for w in self._stage_widgets:
            vx = int(w["spin_x"].get_value())
            vy = int(w["spin_y"].get_value()) if self._separate_xy else vx
            res_x.append(vx)
            res_y.append(vy)

        if getattr(p, "profile_version", None) == 7:
            p.resolutions_x = list(res_x)
            p.resolutions_y = list(res_y)
            p.resolutions = p.resolutions_x
        else:
            p.resolutions = list(res_x)

        # Default & shift indices
        for i, w in enumerate(self._stage_widgets):
            if w["radio_def"].get_active():
                p.resolution_default_index = i
            if w["radio_shift"].get_active():
                p.resolution_shift_index = i

        # Report rate
        rr_id = self._rr_combo.get_active_id()
        if rr_id is not None:
            p.report_rate = int(rr_id)

        # Timeouts
        p.ps_timeout = int(self._ps_timeout_spin.get_value())
        p.po_timeout = int(self._po_timeout_spin.get_value())

    # ---- UI Event Handlers ----

    def _on_profile_selection_changed(self, combo) -> None:
        if self._loading:
            return
        new_id = combo.get_active_id()
        if new_id is not None:
            self._sync_ui_to_profile(self._selected_idx)
            self._selected_idx = int(new_id)
            self._load_profile(self._selected_idx)

    def _on_enabled_toggled(self, chk) -> None:
        if self._loading:
            return
        if self._profiles and self._selected_idx in self._profiles.profiles:
            p = self._profiles.profiles[self._selected_idx]
            new_state = 1 if chk.get_active() else 0
            # Safety guard: ensure at least one profile remains enabled
            if new_state == 0:
                enabled_others = [
                    idx for idx, prof in self._profiles.profiles.items()
                    if idx != self._selected_idx and getattr(prof, "enabled", 0) == 1
                ]
                if not enabled_others:
                    self._show_info(
                        _("At least one profile must remain enabled on the mouse."),
                        Gtk.MessageType.WARNING,
                    )
                    chk.handler_block_by_func(self._on_enabled_toggled)
                    chk.set_active(True)
                    chk.handler_unblock_by_func(self._on_enabled_toggled)
                    return
            p.enabled = new_state

    def _on_dpi_stage_modified(self, idx: int) -> None:
        if self._loading:
            return
        if self._profiles and self._selected_idx in self._profiles.profiles:
            self._sync_ui_to_profile(self._selected_idx)

    def _on_default_radio_toggled(self, radio, idx: int) -> None:
        if self._loading:
            return
        if radio.get_active() and self._profiles and self._selected_idx in self._profiles.profiles:
            self._profiles.profiles[self._selected_idx].resolution_default_index = idx

    def _on_shift_radio_toggled(self, radio, idx: int) -> None:
        if self._loading:
            return
        if radio.get_active() and self._profiles and self._selected_idx in self._profiles.profiles:
            self._profiles.profiles[self._selected_idx].resolution_shift_index = idx

    def _on_separate_xy_toggled(self, chk) -> None:
        if self._loading:
            return
        self._separate_xy = chk.get_active()
        for w in self._stage_widgets:
            if self._separate_xy:
                w["lbl_x"].show()
                w["lbl_y"].show()
                w["spin_y"].show()
            else:
                w["lbl_x"].hide()
                w["lbl_y"].hide()
                w["spin_y"].hide()
                w["spin_y"].set_value(w["spin_x"].get_value())
        self._sync_ui_to_profile(self._selected_idx)

    def _on_report_rate_changed(self, combo) -> None:
        if self._loading:
            return
        rr_id = combo.get_active_id()
        if rr_id is not None and self._profiles and self._selected_idx in self._profiles.profiles:
            self._profiles.profiles[self._selected_idx].report_rate = int(rr_id)

    def _on_timeout_changed(self, _spin) -> None:
        if self._loading:
            return
        if self._profiles and self._selected_idx in self._profiles.profiles:
            p = self._profiles.profiles[self._selected_idx]
            p.ps_timeout = int(self._ps_timeout_spin.get_value())
            p.po_timeout = int(self._po_timeout_spin.get_value())

    def _on_activate_clicked(self, _btn) -> None:
        """Switch mouse to this onboard profile."""
        self._sync_ui_to_profile(self._selected_idx)
        profile_num = self._selected_idx
        setting = next((s for s in getattr(self.device, "settings", []) or [] if s.name == "onboard_profiles"), None)
        if not setting:
            return

        # Ensure the profile is actually valid in the setting choices
        if hasattr(setting, "choices") and setting.choices:
            if not any(int(c) == profile_num for c in setting.choices):
                self._show_info(
                    _("Please click 'Save to Mouse' to enable Profile %d before activating it.") % profile_num,
                    Gtk.MessageType.WARNING,
                )
                return

        from solaar.ui.config_panel import _write_async

        _write_async(setting, profile_num, self.sbox)
        self._refresh_all()
        self._show_info(_("Profile %d activated on mouse.") % profile_num)

    def _on_copy_from_clicked(self, _btn) -> None:
        """Copy settings from another profile into the current profile."""
        if not self._profiles or not getattr(self._profiles, "profiles", None):
            return

        other_profiles = [idx for idx in sorted(self._profiles.profiles.keys()) if idx != self._selected_idx]
        if not other_profiles:
            self._show_info(_("No other profiles available to copy from."), Gtk.MessageType.INFO)
            return

        dialog = Gtk.Dialog(
            title=_("Copy Settings from Profile"),
            parent=self._window,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            _("Copy"),
            Gtk.ResponseType.OK,
        )

        content = dialog.get_content_area()
        content.set_spacing(10)
        content.set_border_width(12)

        lbl = Gtk.Label(label=_("Copy settings to Profile %d from:") % self._selected_idx)
        content.add(lbl)

        combo = Gtk.ComboBoxText()
        for idx in other_profiles:
            combo.append(str(idx), f"{_('Profile')} {idx}")
        combo.set_active(0)
        content.add(combo)

        dialog.show_all()
        response = dialog.run()
        selected_src = combo.get_active_id()
        dialog.destroy()

        if response == Gtk.ResponseType.OK and selected_src:
            src_idx = int(selected_src)
            src_p = self._profiles.profiles[src_idx]
            dst_p = self._profiles.profiles[self._selected_idx]

            rx = getattr(src_p, "resolutions_x", getattr(src_p, "resolutions", [800] * 5))
            ry = getattr(src_p, "resolutions_y", rx)
            dst_p.resolutions_x = list(rx)
            dst_p.resolutions_y = list(ry)
            dst_p.resolutions = list(rx)
            dst_p.resolution_default_index = getattr(src_p, "resolution_default_index", 0)
            dst_p.resolution_shift_index = getattr(src_p, "resolution_shift_index", 0)
            dst_p.report_rate = getattr(src_p, "report_rate", 3)
            dst_p.ps_timeout = getattr(src_p, "ps_timeout", 60)
            dst_p.po_timeout = getattr(src_p, "po_timeout", 300)

            self._load_profile(self._selected_idx)
            self._show_info(
                _("Copied settings from Profile %d. Click 'Save to Mouse' to apply.") % src_idx,
                Gtk.MessageType.INFO,
            )

    def _on_reset_defaults_clicked(self, _btn) -> None:
        """Reset current profile to sensible default values."""
        if not self._profiles or self._selected_idx not in self._profiles.profiles:
            return

        dst_p = self._profiles.profiles[self._selected_idx]
        default_res = [600, 800, 1200, 1400, 1600]
        # Clamp to device range
        default_res = [max(self._min_dpi, min(self._max_dpi, r)) for r in default_res]

        dst_p.resolutions_x = list(default_res)
        dst_p.resolutions_y = list(default_res)
        dst_p.resolutions = list(default_res)
        dst_p.resolution_default_index = 1  # 800 DPI
        dst_p.resolution_shift_index = 0    # 600 DPI
        dst_p.report_rate = 3 if getattr(self._profiles, "profile_version", None) == 7 else 1  # 1000 Hz
        dst_p.ps_timeout = 60
        dst_p.po_timeout = 300

        self._load_profile(self._selected_idx)
        self._show_info(
            _("Reset Profile %d to default settings. Click 'Save to Mouse' to apply.") % self._selected_idx,
            Gtk.MessageType.INFO,
        )

    # ---- Save / Reload / Import / Export Actions ----

    def _set_buttons_sensitive(self, sensitive: bool) -> None:
        self._save_btn.set_sensitive(sensitive)
        self._reload_btn.set_sensitive(sensitive)
        self._import_btn.set_sensitive(sensitive)
        self._export_btn.set_sensitive(sensitive)
        self._copy_btn.set_sensitive(sensitive)
        self._reset_btn.set_sensitive(sensitive)

    def _on_save_clicked(self, _btn) -> None:
        """Write modified profiles to the mouse hardware."""
        if not self._profiles:
            return

        self._sync_ui_to_profile(self._selected_idx)

        # Validate that at least one profile is enabled
        enabled_count = sum(1 for p in self._profiles.profiles.values() if getattr(p, "enabled", 0) == 1)
        if enabled_count == 0:
            self._show_info(_("Cannot save: at least one profile must be enabled."), Gtk.MessageType.ERROR)
            return

        self._set_buttons_sensitive(False)
        self._save_spinner.show()
        self._save_spinner.start()

        def _worker():
            err = None
            written = 0
            try:
                written = self._profiles.write(self.device)
            except Exception as e:
                err = e
                logger.exception("Failed to write onboard profiles to %s", self.device.name)
            GLib.idle_add(self._on_save_finished, written, err)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_save_finished(self, written: int, err: Exception | None) -> None:
        self._save_spinner.stop()
        self._save_spinner.hide()
        self._set_buttons_sensitive(True)

        if err is not None:
            self._show_info(_("Error saving profiles to mouse: %s") % str(err), Gtk.MessageType.ERROR)
            return

        if written > 0:
            self._show_info(
                _("Successfully saved %d sector(s) to %s internal memory!") % (written, self.device.name),
                Gtk.MessageType.INFO,
            )
        else:
            self._show_info(_("Mouse is already up-to-date (no changes needed)."), Gtk.MessageType.INFO)

        # If the active profile on the mouse was edited, reload it into active RAM
        onboard_setting = next((s for s in getattr(self.device, "settings", []) or [] if s.name == "onboard_profiles"), None)
        if onboard_setting:
            active_val = getattr(onboard_setting, "_value", None)
            if not _is_onboard_disabled(active_val):
                active_sector = int(active_val)
                try:
                    self.device.feature_request(
                        hidpp20.SupportedFeature.ONBOARD_PROFILES, 0x30, common.int2bytes(active_sector, 2)
                    )
                except Exception as e:
                    logger.debug("Feature 0x30 reload error: %s", e)
                settings_templates.profile_change(self.device, active_sector)

            # Rebuild setting choices in case profiles were enabled/disabled
            try:
                headers = hidpp20.OnboardProfiles.get_profile_headers(self.device)
            except Exception as e:
                logger.debug("get_profile_headers exception: %s", e)
                headers = None
            if headers:
                profiles_list = [onboard_setting.choices_universe[0]]
                for sector, enabled in headers:
                    if enabled and onboard_setting.choices_universe[sector]:
                        profiles_list.append(onboard_setting.choices_universe[sector])
                new_choices = common.NamedInts.list(profiles_list)
                if hasattr(onboard_setting, "_validator") and onboard_setting._validator is not None:
                    onboard_setting._validator.choices = new_choices
                if self.sbox and hasattr(self.sbox, "_control") and hasattr(self.sbox._control, "set_choices"):
                    self.sbox._control.set_choices(new_choices)
                    if active_val is not None:
                        # Fallback to disabled if previous active profile was disabled
                        if any(int(c) == int(active_val) for c in new_choices):
                            self.sbox._control.set_value(active_val)
                        else:
                            self.sbox._control.set_value(0)

        self._refresh_all()

    def _on_reload_clicked(self, _btn) -> None:
        """Re-read profiles from device memory."""
        self._set_buttons_sensitive(False)
        self._save_spinner.show()
        self._save_spinner.start()

        def _worker():
            err = None
            try:
                self.device._profiles = None
                profiles = self.device.profiles
            except Exception as e:
                err = e
                profiles = None
            GLib.idle_add(self._on_reload_finished, profiles, err)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_reload_finished(self, profiles, err: Exception | None) -> None:
        self._save_spinner.stop()
        self._save_spinner.hide()
        self._set_buttons_sensitive(True)

        if err is not None or not profiles:
            self._show_info(_("Failed to reload profiles from mouse: %s") % str(err), Gtk.MessageType.ERROR)
            return

        self._profiles = profiles
        self._refresh_all()
        self._show_info(_("Profiles successfully reloaded from mouse memory."), Gtk.MessageType.INFO)

    def _on_export_yaml(self, _btn) -> None:
        """Export current profiles to a YAML file."""
        if not self._profiles:
            return

        self._sync_ui_to_profile(self._selected_idx)

        chooser = Gtk.FileChooserDialog(
            title=_("Export Onboard Profiles to YAML"),
            parent=self._window,
            action=Gtk.FileChooserAction.SAVE,
        )
        chooser.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE,
            Gtk.ResponseType.OK,
        )
        chooser.set_do_overwrite_confirmation(True)

        safe_name = "".join(c for c in getattr(self.device, "name", "device") if c.isalnum() or c in (" ", "_", "-")).strip()
        safe_name = safe_name.replace(" ", "_") or "device"
        default_filename = f"{safe_name}_profiles.yaml"
        chooser.set_current_name(default_filename)

        filter_yaml = Gtk.FileFilter()
        filter_yaml.set_name(_("YAML files (*.yaml, *.yml)"))
        filter_yaml.add_pattern("*.yaml")
        filter_yaml.add_pattern("*.yml")
        chooser.add_filter(filter_yaml)

        response = chooser.run()
        if response == Gtk.ResponseType.OK:
            filename = chooser.get_filename()
            chooser.destroy()
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    yaml.dump(self._profiles, f)
                self._show_info(_("Exported profiles to %s") % filename, Gtk.MessageType.INFO)
            except Exception as e:
                self._show_info(_("Error exporting profiles: %s") % str(e), Gtk.MessageType.ERROR)
        else:
            chooser.destroy()

    def _on_import_yaml(self, _btn) -> None:
        """Import profiles from a YAML file."""
        chooser = Gtk.FileChooserDialog(
            title=_("Import Onboard Profiles from YAML"),
            parent=self._window,
            action=Gtk.FileChooserAction.OPEN,
        )
        chooser.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )

        filter_yaml = Gtk.FileFilter()
        filter_yaml.set_name(_("YAML files (*.yaml, *.yml)"))
        filter_yaml.add_pattern("*.yaml")
        filter_yaml.add_pattern("*.yml")
        chooser.add_filter(filter_yaml)

        response = chooser.run()
        if response == Gtk.ResponseType.OK:
            filename = chooser.get_filename()
            chooser.destroy()
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)

                dev_prof_ver = getattr(self._profiles, "profile_version", None)

                # Case A: Full OnboardProfiles structure
                if isinstance(loaded, hidpp20.OnboardProfiles):
                    file_ver = getattr(loaded, "profile_version", None)
                    if dev_prof_ver is not None and file_ver != dev_prof_ver:
                        self._show_info(
                            _("Profile format mismatch: file has format %s, device requires format %s.")
                            % (file_ver, dev_prof_ver),
                            Gtk.MessageType.ERROR,
                        )
                        return
                    self._profiles = loaded
                    self._refresh_all()
                    self._show_info(
                        _("Imported profiles from %s. Click 'Save to Mouse' to apply.") % filename,
                        Gtk.MessageType.INFO,
                    )
                # Case B: Single OnboardProfile loaded into current selected slot
                elif isinstance(loaded, hidpp20.OnboardProfile):
                    file_ver = getattr(loaded, "profile_version", None)
                    if dev_prof_ver is not None and file_ver != dev_prof_ver:
                        self._show_info(
                            _("Profile format mismatch: file has format %s, device requires format %s.")
                            % (file_ver, dev_prof_ver),
                            Gtk.MessageType.ERROR,
                        )
                        return
                    if self._profiles and self._selected_idx in self._profiles.profiles:
                        loaded.sector = self._profiles.profiles[self._selected_idx].sector
                        self._profiles.profiles[self._selected_idx] = loaded
                        self._load_profile(self._selected_idx)
                        self._show_info(
                            _("Imported Profile %d from %s. Click 'Save to Mouse' to apply.")
                            % (self._selected_idx, filename),
                            Gtk.MessageType.INFO,
                        )
                else:
                    self._show_info(
                        _("Selected file does not contain valid OnboardProfiles."),
                        Gtk.MessageType.ERROR,
                    )
            except Exception as e:
                self._show_info(_("Error importing profiles: %s") % str(e), Gtk.MessageType.ERROR)
        else:
            chooser.destroy()
