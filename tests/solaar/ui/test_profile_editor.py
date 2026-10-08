## Copyright (C) 2026  Solaar Contributors
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

from unittest import mock
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
import pytest
import yaml

from logitech_receiver import common
from logitech_receiver import hidpp20
from logitech_receiver import hidpp20_constants
from logitech_receiver import settings_templates
from solaar.ui import config_panel
from solaar.ui import profile_editor


RAW_SECTOR_1 = bytes.fromhex(
    "0303040158025802002003200300b004b004007805780500400640060000000000ff00ffffffffff"
    "ffffffff3c002c01800100018001000280010004800100088001001090050000ffffffffffffffff"
    "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    "ffffffffffffffff0300000000001f400000000300000000001f400000000300000000001f403200"
    "000300000000001f40320000036d41"
)


def _make_format7_device():
    p1 = hidpp20.OnboardProfile.from_bytes(1, 1, 6, 0, RAW_SECTOR_1, profile_version=7)
    p2 = hidpp20.OnboardProfile.from_bytes(2, 0, 6, 0, RAW_SECTOR_1, profile_version=7)

    profiles = hidpp20.OnboardProfiles(
        version=hidpp20.OnboardProfilesVersion,
        profile_version=7,
        name="G304 X LIGHTSPEED",
        count=2,
        buttons=6,
        gbuttons=0,
        sectors=16,
        size=255,
        profiles={1: p1, 2: p2},
    )

    dev = mock.MagicMock()
    dev.name = "G304 X LIGHTSPEED"
    dev.online = True
    dev.profiles = profiles
    dev.unitId = "8686ADE9"

    s_onboard = mock.MagicMock()
    s_onboard.name = "onboard_profiles"
    s_onboard._value = common.NamedInt(1, "Profile 1")
    s_onboard.choices_universe = common.NamedInts(Disabled=0, **{"Profile 1": 1, "Profile 2": 2})

    s_onboard.description = "Enable an onboard profile"
    s_onboard.label = "Onboard Profiles"
    s_onboard.display = True
    s_onboard.kind = 3
    s_onboard.editor_class = "solaar.ui.profile_editor:OnboardProfilesControl"
    s_onboard._device = dev

    validator = mock.MagicMock()
    validator.choices = common.NamedInts.list([common.NamedInt(0, "Disabled"), common.NamedInt(1, "Profile 1")])
    s_onboard._validator = validator
    s_onboard.choices = validator.choices

    s_dpi = mock.MagicMock()
    s_dpi.name = "dpi_extended"
    s_dpi.choices = {0: [100, 200, 600, 800, 1200, 1400, 1600, 3200, 25600]}

    dev.settings = [s_onboard, s_dpi]
    return dev, profiles, s_onboard


def test_onboard_profiles_control_protocol():
    dev, profiles, s_onboard = _make_format7_device()

    sbox = mock.MagicMock()
    sbox.setting = s_onboard
    s_onboard._device = dev

    ctrl = profile_editor.OnboardProfilesControl(sbox)
    assert isinstance(ctrl, Gtk.Box)
    assert hasattr(ctrl, "combo_box")
    assert hasattr(ctrl, "edit_btn")

    # Choices and values
    ctrl.set_choices(s_onboard.choices)
    ctrl.set_value(common.NamedInt(1, "Profile 1"))
    assert ctrl.get_value() == 1

    ctrl.set_value(0)
    assert ctrl.get_value() == 0

    # Sensitivity
    ctrl.set_sensitive(False)
    assert ctrl.combo_box.get_sensitive() is False
    assert ctrl.edit_btn.get_sensitive() is True  # Device is online, edit button stays usable

    ctrl.set_sensitive(True)
    assert ctrl.combo_box.get_sensitive() is True
    assert ctrl.edit_btn.get_sensitive() is True


def test_onboard_profiles_control_layout_and_create_sbox():
    dev, profiles, s_onboard = _make_format7_device()
    sbox = config_panel._create_sbox(s_onboard, dev)
    assert sbox is not None
    assert isinstance(sbox._control, profile_editor.OnboardProfilesControl)


def test_dialog_load_and_edit_format7():
    dev, profiles, s_onboard = _make_format7_device()
    dlg = profile_editor.OnboardProfileEditorDialog("test_key_fmt7", dev)
    dlg.present()

    try:
        # Check initial profile 1 values loaded into UI
        assert dlg._profile_combo.get_active_id() == "1"
        assert dlg._enabled_chk.get_active() is True
        assert dlg._stage_widgets[0]["spin_x"].get_value() == 600
        assert dlg._stage_widgets[1]["spin_x"].get_value() == 800
        assert dlg._stage_widgets[2]["spin_x"].get_value() == 1200
        assert dlg._stage_widgets[3]["spin_x"].get_value() == 1400
        assert dlg._stage_widgets[4]["spin_x"].get_value() == 1600
        assert dlg._stage_widgets[3]["radio_def"].get_active() is True
        assert dlg._stage_widgets[4]["radio_shift"].get_active() is True
        assert dlg._rr_combo.get_active_id() == "3"  # 1ms (1000Hz)
        assert dlg._ps_timeout_spin.get_value() == 60
        assert dlg._po_timeout_spin.get_value() == 300

        # Edit DPI values
        dlg._stage_widgets[0]["spin_x"].set_value(700)
        dlg._stage_widgets[1]["spin_x"].set_value(900)
        dlg._stage_widgets[0]["radio_def"].set_active(True)
        dlg._stage_widgets[1]["radio_shift"].set_active(True)
        dlg._rr_combo.set_active_id("2")  # 500Hz
        dlg._ps_timeout_spin.set_value(90)

        # Sync to memory
        dlg._sync_ui_to_profile(1)
        p1 = profiles.profiles[1]
        assert p1.resolutions_x[0] == 700
        assert p1.resolutions_x[1] == 900
        assert p1.resolutions[0] == 700
        assert p1.resolution_default_index == 0
        assert p1.resolution_shift_index == 1
        assert p1.report_rate == 2
        assert p1.ps_timeout == 90

        # Switch to profile 2
        dlg._profile_combo.set_active_id("2")
        assert dlg._selected_idx == 2
        assert dlg._enabled_chk.get_active() is False

        # Enable profile 2 and modify stage 1
        dlg._enabled_chk.set_active(True)
        dlg._stage_widgets[0]["spin_x"].set_value(1000)
        dlg._sync_ui_to_profile(2)
        p2 = profiles.profiles[2]
        assert p2.enabled == 1
        assert p2.resolutions_x[0] == 1000

        # Separate X/Y DPI
        dlg._sep_xy_chk.set_active(True)
        assert dlg._separate_xy is True
        dlg._stage_widgets[0]["spin_y"].set_value(1200)
        dlg._sync_ui_to_profile(2)
        assert p2.resolutions_x[0] == 1000
        assert p2.resolutions_y[0] == 1200

    finally:
        dlg._destroy()


def test_dialog_save_to_device():
    dev, profiles, s_onboard = _make_format7_device()
    sbox = config_panel._create_sbox(s_onboard, dev)

    dev.profiles.write = mock.MagicMock(return_value=1)
    dev.feature_request = mock.MagicMock(return_value=b"\xff\xff")

    dlg = profile_editor.OnboardProfileEditorDialog("test_key_save", dev, sbox=sbox)
    dlg.present()

    try:
        dlg._stage_widgets[0]["spin_x"].set_value(750)
        dlg._on_save_finished(1, None)

        # Verify info bar feedback
        assert dlg._infobar.get_visible() is True
        assert "1 sector" in dlg._infobar_label.get_text()

    finally:
        dlg._destroy()


def test_dialog_save_error_feedback():
    dev, profiles, s_onboard = _make_format7_device()
    dlg = profile_editor.OnboardProfileEditorDialog("test_key_err", dev)
    dlg.present()

    try:
        dlg._on_save_finished(0, RuntimeError("Communication timeout"))
        assert dlg._infobar.get_visible() is True
        assert "Communication timeout" in dlg._infobar_label.get_text()
    finally:
        dlg._destroy()


def test_dialog_backwards_compatibility_format3():
    p_old = hidpp20.OnboardProfile(
        sector=1,
        enabled=1,
        report_rate=1,  # 1ms in format < 7
        resolution_default_index=2,
        resolution_shift_index=0,
        resolutions=[400, 800, 1600, 3200, 6400],
        red=0,
        green=0,
        blue=0,
        power_mode=0,
        angle_snap=0,
        write_count=0,
        reserved=b"\x00" * 8,
        ps_timeout=60,
        po_timeout=300,
        buttons=[],
        gbuttons=[],
        name="G502 Profile",
        lighting=[],
        profile_version=3,
    )

    profiles = hidpp20.OnboardProfiles(
        version=hidpp20.OnboardProfilesVersion,
        profile_version=3,
        name="G502 HERO",
        count=1,
        buttons=6,
        gbuttons=0,
        sectors=16,
        size=255,
        profiles={1: p_old},
    )

    dev = mock.MagicMock()
    dev.name = "G502 HERO"
    dev.online = True
    dev.profiles = profiles

    dlg = profile_editor.OnboardProfileEditorDialog("test_key_old", dev)
    dlg.present()

    try:
        assert dlg._stage_widgets[0]["spin_x"].get_value() == 400
        assert dlg._stage_widgets[1]["spin_x"].get_value() == 800
        assert dlg._stage_widgets[2]["spin_x"].get_value() == 1600
        assert dlg._stage_widgets[3]["spin_x"].get_value() == 3200
        assert dlg._stage_widgets[4]["spin_x"].get_value() == 6400
        assert dlg._stage_widgets[2]["radio_def"].get_active() is True
        assert dlg._stage_widgets[0]["radio_shift"].get_active() is True
        assert dlg._rr_combo.get_active_id() == "1"

        # Edit DPI and sync
        dlg._stage_widgets[0]["spin_x"].set_value(450)
        dlg._sync_ui_to_profile(1)
        assert p_old.resolutions[0] == 450
    finally:
        dlg._destroy()


def test_dialog_registry_caching():
    dev, profiles, s_onboard = _make_format7_device()

    dlg1 = profile_editor.get_profile_dialog(dev)
    dlg2 = profile_editor.get_profile_dialog(dev)
    assert dlg1 is dlg2

    dlg1._on_delete(None, None)
    dlg3 = profile_editor.get_profile_dialog(dev)
    assert dlg3 is not dlg1
    dlg3._destroy()


def test_dialog_separate_xy_preservation_on_load():
    dev, profiles, s_onboard = _make_format7_device()
    # Profile 1 has distinct X and Y DPI
    profiles.profiles[1].resolutions_x = [600, 800, 1200, 1400, 1600]
    profiles.profiles[1].resolutions_y = [700, 900, 1300, 1500, 1700]

    dlg = profile_editor.OnboardProfileEditorDialog("test_sep_xy_load", dev)
    dlg.present()

    try:
        assert dlg._sep_xy_chk.get_active() is True
        assert dlg._separate_xy is True
        assert dlg._stage_widgets[0]["lbl_y"].get_visible() is True
        assert dlg._stage_widgets[0]["spin_y"].get_visible() is True
        assert dlg._stage_widgets[0]["spin_x"].get_value() == 600
        assert dlg._stage_widgets[0]["spin_y"].get_value() == 700

        # Sync back to profile object
        dlg._sync_ui_to_profile(1)
        assert profiles.profiles[1].resolutions_x == [600, 800, 1200, 1400, 1600]
        assert profiles.profiles[1].resolutions_y == [700, 900, 1300, 1500, 1700]
    finally:
        dlg._destroy()


def test_dialog_activate_profile_disabled_guard():
    dev, profiles, s_onboard = _make_format7_device()
    dlg = profile_editor.OnboardProfileEditorDialog("test_act_guard", dev)
    dlg.present()

    try:
        # Profile 1 is current active
        assert dlg._selected_idx == 1
        assert dlg._activate_btn.get_sensitive() is False
        assert dlg._activate_btn.get_label() == "Current Active"

        # Switch to Profile 2 (which is disabled in device choices)
        dlg._profile_combo.set_active_id("2")
        assert dlg._selected_idx == 2
        # Should be disabled with guidance tooltip
        assert dlg._activate_btn.get_sensitive() is False
        assert "before activating" in dlg._activate_btn.get_tooltip_text()
    finally:
        dlg._destroy()


def test_dialog_at_least_one_profile_enabled_guard():
    dev, profiles, s_onboard = _make_format7_device()
    dlg = profile_editor.OnboardProfileEditorDialog("test_min_enabled", dev)
    dlg.present()

    try:
        # Only profile 1 is enabled
        assert profiles.profiles[1].enabled == 1
        assert profiles.profiles[2].enabled == 0

        # Attempt to disable profile 1
        dlg._enabled_chk.set_active(False)
        # Should be blocked, remaining active
        assert dlg._enabled_chk.get_active() is True
        assert profiles.profiles[1].enabled == 1
        assert dlg._infobar.get_visible() is True
        assert "At least one profile must remain enabled" in dlg._infobar_label.get_text()
    finally:
        dlg._destroy()




def test_dialog_live_dpi_notification_updates_badge():
    dev, profiles, s_onboard = _make_format7_device()
    dlg = profile_editor.get_profile_dialog(dev)
    dlg.present()

    try:
        # Current active profile is 1. Stages: [600, 800, 1200, 1400, 1600]
        # Notify 1200 DPI (Stage 3)
        dlg.update_active_dpi_from_value({0: 1200, 1: 1200})
        assert dlg._stage_widgets[0]["badge"].get_visible() is False
        assert dlg._stage_widgets[1]["badge"].get_visible() is False
        assert dlg._stage_widgets[2]["badge"].get_visible() is True
        assert dlg._stage_widgets[3]["badge"].get_visible() is False

        # Notify 600 DPI (Stage 1)
        dlg.update_active_dpi_from_value(600)
        assert dlg._stage_widgets[0]["badge"].get_visible() is True
        assert dlg._stage_widgets[2]["badge"].get_visible() is False
    finally:
        dlg._destroy()


def test_ui_gating_blocks_dpi_in_onboard_mode(mocker):
    from solaar.ui import config_panel

    dev = mocker.MagicMock()
    dev.persister = None

    s_onboard = mocker.MagicMock()
    s_onboard.name = "onboard_profiles"
    s_onboard._value = common.NamedInt(1, "Profile 1")
    dev.settings = [s_onboard]

    assert config_panel._gate_blocks(dev, "dpi_extended") is True
    assert config_panel._gate_blocks(dev, "report_rate_extended") is True
    assert config_panel._gate_blocks(dev, "dpi") is True
    assert config_panel._gate_blocks(dev, "report_rate") is True


def test_ui_gating_allows_dpi_in_host_mode(mocker):
    from solaar.ui import config_panel

    dev = mocker.MagicMock()
    dev.persister = None

    s_onboard = mocker.MagicMock()
    s_onboard.name = "onboard_profiles"
    s_onboard._value = common.NamedInt(0, "Disabled")
    dev.settings = [s_onboard]

    assert config_panel._gate_blocks(dev, "dpi_extended") is False
    assert config_panel._gate_blocks(dev, "report_rate_extended") is False


def test_map_choice_control_sensitivity(mocker):
    from solaar.ui import config_panel

    sbox = mocker.MagicMock()
    choices = common.NamedInts(X=0, Y=1)
    val_choices = common.NamedInts(DPI1=800, DPI2=1600)
    sbox.setting.choices = {0: val_choices, 1: val_choices}
    sbox.setting._value = {0: 800, 1: 800}

    ctrl = config_panel.MapChoiceControl(sbox)
    ctrl.set_sensitive(False)
    assert ctrl.keyBox.get_sensitive() is False
    assert ctrl.valueBox.get_sensitive() is False

    # set_value must not re-enable valueBox when parent is insensitive
    ctrl.set_value({0: 1600})
    assert ctrl.valueBox.get_sensitive() is False

    ctrl.set_sensitive(True)
    assert ctrl.keyBox.get_sensitive() is True
    assert ctrl.valueBox.get_sensitive() is True


