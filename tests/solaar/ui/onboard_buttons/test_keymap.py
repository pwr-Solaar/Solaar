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

"""Unit tests for solaar.ui.onboard_buttons.keymap's mouse-click support.

The Consumer-Control-key tests that motivated this module's third Button
wire type live alongside it; these focus on the mouse-click type added
after it, plus is_left_click(), which the dialog's left-click safety check
depends on.
"""

from __future__ import annotations

from logitech_receiver import hidpp20
from solaar.ui.onboard_buttons import keymap


def test_available_keys_mouse_group_comes_first_with_left_click_on_top():
    keys = keymap.available_keys()
    mouse_entries = [(name, code) for name, code, kind in keys if kind == "mouse"]

    # Left Click leading the very first group is deliberate: "put Left
    # Click back on this button" is the single most important recovery
    # action this editor needs to make easy to find.
    assert keys[0][2] == "mouse"
    assert mouse_entries[0][0] == "Left Click"
    assert {name for name, _ in mouse_entries} == {
        "Left Click",
        "Right Click",
        "Middle Click",
        "Mouse Back",
        "Mouse Forward",
    }


def test_manual_mouse_button_round_trips_through_the_real_wire_format():
    mouse_codes = {name: code for name, code, kind in keymap.available_keys() if kind == "mouse"}
    button = keymap.manual_mouse_button(mouse_codes["Left Click"])

    raw = button.to_bytes()
    # behavior=SEND (0x8) << 4, type=BUTTON (0x1), then the 2-byte code --
    # no modifiers byte, unlike a keyboard key.
    assert raw == bytes([0x80, 0x01, 0x00, 0x01])

    round_tripped = hidpp20.Button.from_bytes(raw)
    assert keymap.is_left_click(round_tripped)
    assert keymap.describe(round_tripped) == "Left Click"


def test_is_left_click_only_true_for_the_left_click_mouse_button():
    mouse_codes = {name: code for name, code, kind in keymap.available_keys() if kind == "mouse"}
    key_codes = {name: code for name, code, kind in keymap.available_keys() if kind == "key"}

    left_click = keymap.manual_mouse_button(mouse_codes["Left Click"])
    right_click = keymap.manual_mouse_button(mouse_codes["Right Click"])
    a_key = keymap.manual_button(key_codes["A"])
    unassigned = keymap.unassigned_button()

    assert keymap.is_left_click(left_click) is True
    assert keymap.is_left_click(right_click) is False
    assert keymap.is_left_click(a_key) is False
    assert keymap.is_left_click(unassigned) is False
    assert keymap.is_left_click(None) is False


def test_mouse_button_code_is_none_for_other_button_kinds():
    key_codes = {name: code for name, code, kind in keymap.available_keys() if kind == "key"}
    consumer_codes = {name: code for name, code, kind in keymap.available_keys() if kind == "consumer"}

    a_key = keymap.manual_button(key_codes["A"])
    browser_back = keymap.manual_consumer_button(consumer_codes["Browser Back"])

    assert keymap.mouse_button_code(a_key) is None
    assert keymap.mouse_button_code(browser_back) is None
    assert keymap.key_and_modifiers(browser_back) == (None, 0)
    assert keymap.consumer_code(a_key) is None
