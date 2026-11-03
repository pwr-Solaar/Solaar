import textwrap

from unittest import mock
from unittest.mock import mock_open

import pytest

from logitech_receiver import diversion
from logitech_receiver.base import HIDPPNotification
from logitech_receiver.hidpp20_constants import SupportedFeature


@pytest.fixture
def rule_config():
    rule_content = """
    %YAML 1.3
    ---
    - MouseGesture: Mouse Left
    - KeyPress:
      - [Control_L, Alt_L, Left]
      - click
    ...
    ---
    - MouseGesture: Mouse Up
    - KeyPress:
      - [Super_L, Up]
      - click
    ...
    ---
    - Test: [thumb_wheel_up, 10]
    - KeyPress:
      - [Control_L, Page_Down]
      - click
    ...
    ---
    """
    return textwrap.dedent(rule_content)


def test_load_rule_config(rule_config):
    expected_rules = [
        [
            diversion.MouseGesture,
            diversion.KeyPress,
        ],
        [diversion.MouseGesture, diversion.KeyPress],
        [diversion.Test, diversion.KeyPress],
    ]

    with mock.patch("builtins.open", new=mock_open(read_data=rule_config)):
        loaded_rules = diversion._load_rule_config(file_path=mock.Mock())

    assert len(loaded_rules.components) == 2  # predefined and user configured rules
    user_configured_rules = loaded_rules.components[0]
    assert isinstance(user_configured_rules, diversion.Rule)

    for components, expected_components in zip(user_configured_rules.components, expected_rules):
        for component, expected_component in zip(components.components, expected_components):
            assert isinstance(component, expected_component)


def test_diversion_rule():
    args = [
        {
            "Rule": [  # Implement problematic keys for Craft and MX Master
                {"Rule": [{"Key": ["Brightness Down", "pressed"]}, {"KeyPress": "XF86_MonBrightnessDown"}]},
                {"Rule": [{"Key": ["Brightness Up", "pressed"]}, {"KeyPress": "XF86_MonBrightnessUp"}]},
            ]
        },
    ]

    rule = diversion.Rule(args)

    assert len(rule.components) == 1
    root_rule = rule.components[0]
    assert isinstance(root_rule, diversion.Rule)

    assert len(root_rule.components) == 2
    for component in root_rule.components:
        assert isinstance(component, diversion.Rule)
        assert len(component.components) == 2

        key = component.components[0]
        assert isinstance(key, diversion.Key)
        key = component.components[1]
        assert isinstance(key, diversion.KeyPress)


def test_key_is_down():
    result = diversion.key_is_down(key=diversion.CONTROL.G2)

    assert result is False


def test_feature():
    expected_data = {"Feature": "CONFIG CHANGE"}

    result = diversion.Feature("CONFIG_CHANGE")

    assert result.data() == expected_data


@pytest.mark.skipif(diversion.evdev is None, reason="uinput is unavailable")
def test_uinput_capabilities_separate_keyboard_repeat_from_mouse_buttons():
    keyboard = diversion.keyboard_devicecap
    mouse = diversion.mouse_devicecap

    assert diversion.evdev.ecodes.EV_REP in keyboard
    assert keyboard[diversion.evdev.ecodes.EV_REP] == []
    assert diversion.evdev.ecodes.EV_REL not in keyboard
    assert diversion.evdev.ecodes.EV_REP not in mouse
    assert diversion.evdev.ecodes.EV_REL in mouse
    assert diversion.buttons["left"][1] in mouse[diversion.evdev.ecodes.EV_KEY]


@pytest.mark.skipif(diversion.evdev is None, reason="uinput is unavailable")
def test_uinput_routes_keyboard_and_mouse_events_to_separate_devices():
    keyboard = mock.Mock()
    mouse = mock.Mock()
    devices = {"solaar-keyboard": keyboard, "solaar-mouse": mouse}
    uinput = diversion.UInput()

    with mock.patch.object(
        diversion.evdev.uinput,
        "UInput",
        side_effect=lambda *, events, name: devices[name],
    ) as create:
        assert uinput.key(diversion.evdev.ecodes.KEY_DELETE + 8, 1)
        assert uinput.click(diversion.buttons["left"], 1)
        assert uinput.scroll(3, -2)

    create.assert_has_calls(
        [
            mock.call(events=diversion.keyboard_devicecap, name="solaar-keyboard"),
            mock.call(events=diversion.mouse_devicecap, name="solaar-mouse"),
        ]
    )
    assert create.call_count == 2
    keyboard.write.assert_called_once_with(diversion.evdev.ecodes.EV_KEY, diversion.evdev.ecodes.KEY_DELETE, 1)
    assert mouse.write.call_args_list == [
        mock.call(diversion.evdev.ecodes.EV_KEY, diversion.buttons["left"][1], 1),
        mock.call(diversion.evdev.ecodes.EV_KEY, diversion.buttons["left"][1], 0),
        mock.call(diversion.evdev.ecodes.EV_REL, diversion.evdev.ecodes.REL_HWHEEL, 3),
        mock.call(diversion.evdev.ecodes.EV_REL, diversion.evdev.ecodes.REL_WHEEL, -2),
    ]


@pytest.mark.skipif(diversion.evdev is None, reason="uinput is unavailable")
def test_uinput_write_failure_only_resets_the_failed_device():
    keyboard = mock.Mock()
    mouse = mock.Mock()
    keyboard.write.side_effect = OSError("write failed")
    devices = {"solaar-keyboard": keyboard, "solaar-mouse": mouse}
    uinput = diversion.UInput()

    with mock.patch.object(
        diversion.evdev.uinput,
        "UInput",
        side_effect=lambda *, events, name: devices[name],
    ):
        assert uinput.click(diversion.buttons["left"], 1)
        assert not uinput.key(diversion.evdev.ecodes.KEY_A + 8, 1)

    keyboard.close.assert_called_once_with()
    assert uinput._keyboard.udevice is None
    assert uinput._mouse.udevice is mouse


@pytest.fixture
def simulated_input(monkeypatch):
    if diversion.evdev is None:
        pytest.skip("uinput is unavailable")
    keyboard, mouse = mock.Mock(), mock.Mock()
    devices = {"solaar-keyboard": keyboard, "solaar-mouse": mouse}
    monkeypatch.setattr(diversion.evdev.uinput, "UInput", lambda *, events, name: devices[name])
    uinput = diversion.UInput()
    monkeypatch.setattr(diversion, "uinput", uinput)
    return uinput, keyboard, mouse


def test_cleanup_releases_only_held_keys_in_reverse_press_order(simulated_input):
    uinput, keyboard, mouse = simulated_input
    codes = diversion.evdev.ecodes
    assert uinput.key(codes.KEY_LEFTCTRL + 8, 1)
    assert uinput.key(codes.KEY_DELETE + 8, 1)
    assert uinput.key(codes.KEY_A + 8, 1)
    assert uinput.key(codes.KEY_A + 8, 0)
    assert uinput.click(diversion.buttons["left"], diversion.DEPRESS)
    keyboard.write.reset_mock()
    mouse.write.reset_mock()

    uinput.release_all()

    assert keyboard.write.call_args_list == [
        mock.call(codes.EV_KEY, codes.KEY_DELETE, 0),
        mock.call(codes.EV_KEY, codes.KEY_LEFTCTRL, 0),
    ]
    mouse.write.assert_called_once_with(codes.EV_KEY, diversion.buttons["left"][1], 0)
    assert not uinput._keyboard._held_keys
    assert not uinput._mouse._held_keys
    keyboard.write.reset_mock()
    mouse.write.reset_mock()
    uinput.release_all()
    keyboard.write.assert_not_called()
    mouse.write.assert_not_called()


def test_idle_cleanup_does_not_create_virtual_devices():
    uinput = diversion.UInput()
    with mock.patch.object(uinput._keyboard, "setup") as keyboard, mock.patch.object(uinput._mouse, "setup") as mouse:
        uinput.release_all()
    keyboard.assert_not_called()
    mouse.assert_not_called()


def test_failed_cleanup_closes_device_and_does_not_recreate_it(simulated_input):
    uinput, keyboard, mouse = simulated_input
    assert uinput.key(diversion.evdev.ecodes.KEY_DELETE + 8, 1)
    keyboard.write.side_effect = OSError("disconnected")
    uinput.release_all()
    keyboard.close.assert_called_once_with()
    assert uinput._keyboard.udevice is None
    assert not uinput._keyboard._held_keys
    with mock.patch.object(uinput._keyboard, "setup") as setup:
        uinput.release_all()
    setup.assert_not_called()


@pytest.mark.parametrize("operation", ["reload", "save", "edit", "stop"])
def test_rule_lifecycle_releases_held_input(operation, simulated_input, monkeypatch, tmp_path):
    uinput, keyboard, mouse = simulated_input
    codes = diversion.evdev.ecodes
    assert uinput.key(codes.KEY_DELETE + 8, 1)
    keyboard.write.reset_mock()
    if operation == "reload":
        monkeypatch.setattr(diversion, "_file_path", str(tmp_path / "missing.yaml"))
        diversion.load_config_rule_file()
    elif operation == "save":
        assert diversion._save_config_rule_file(str(tmp_path / "rules.yaml"))
    elif operation == "edit":
        from solaar.ui.diversion_rules import DiversionDialog

        DiversionDialog.on_update(mock.Mock())
    else:
        from solaar import listener

        monkeypatch.setattr(listener, "_all_listeners", {})
        listener.stop_all()
    keyboard.write.assert_called_once_with(codes.EV_KEY, codes.KEY_DELETE, 0)


@pytest.mark.skipif(diversion.evdev is None, reason="uinput is unavailable")
def test_uinput_repeats_depressed_scroll_until_release(scroll_input):
    uinput, mouse, timeout_add, source_remove = scroll_input
    source = (mock.Mock(receiver=None), 123, (-1, 0))
    assert uinput.scroll(-1, 0, diversion.DEPRESS, source)
    repeat = next(iter(uinput._scroll_repeats.values()))
    timeout_add.assert_called_once_with(250, uinput._repeat_scroll, repeat)
    assert not uinput._repeat_scroll(repeat)
    assert timeout_add.call_args_list[-1] == mock.call(33, uinput._repeat_scroll, repeat)
    assert uinput.scroll(-1, 0, diversion.RELEASE, source)
    assert mouse.write.call_count == 2
    source_remove.assert_called_once_with(102)
    assert not uinput._scroll_repeats


@pytest.fixture
def scroll_input(simulated_input, monkeypatch):
    uinput, keyboard, mouse = simulated_input
    timeout_add = mock.Mock(side_effect=range(101, 1001))
    source_remove = mock.Mock()
    monkeypatch.setattr(diversion.GLib, "timeout_add", timeout_add)
    monkeypatch.setattr(diversion.GLib, "source_remove", source_remove)
    return uinput, mouse, timeout_add, source_remove


def test_scroll_release_is_independent_of_numeric_multiplier(scroll_input):
    uinput, mouse, timeout_add, source_remove = scroll_input
    device = mock.Mock(receiver=None)
    uinput._scroll_keys = (123, None)
    diversion.MouseScroll([[1, 0], diversion.DEPRESS]).evaluate(None, None, device, 2)
    repeat = next(iter(uinput._scroll_repeats.values()))
    assert repeat.amounts == (2, 0)
    uinput._scroll_keys = (None, 123)
    diversion.MouseScroll([[1, 0], diversion.RELEASE]).evaluate(None, None, device, 1)
    assert not uinput._scroll_repeats
    source_remove.assert_called_once_with(101)
    assert mouse.write.call_count == 1


def test_duplicate_depress_cancels_old_timer_and_ignores_stale_callback(scroll_input):
    uinput, mouse, timeout_add, source_remove = scroll_input
    source = (mock.Mock(receiver=None), 123, (-1, 0))
    assert uinput.scroll(-1, 0, diversion.DEPRESS, source)
    old = next(iter(uinput._scroll_repeats.values()))
    assert uinput.scroll(-2, 0, diversion.DEPRESS, source)
    assert len(uinput._scroll_repeats) == 1
    source_remove.assert_called_once_with(101)
    mouse.write.reset_mock()
    assert not uinput._repeat_scroll(old)
    mouse.write.assert_not_called()
    assert timeout_add.call_count == 2


def test_scroll_repeat_write_failure_stops_timer(scroll_input):
    uinput, mouse, timeout_add, source_remove = scroll_input
    assert uinput.scroll(-1, 0, diversion.DEPRESS, (mock.Mock(receiver=None), 123, (-1, 0)))
    repeat = next(iter(uinput._scroll_repeats.values()))
    mouse.write.side_effect = OSError("device gone")
    assert not uinput._repeat_scroll(repeat)
    assert not uinput._scroll_repeats
    assert timeout_add.call_count == 1
    mouse.close.assert_called_once_with()


def test_scroll_release_without_a_hold_and_zero_depress_are_idle(scroll_input):
    uinput, mouse, timeout_add, source_remove = scroll_input
    source = (mock.Mock(receiver=None), 123, (0, 0))
    assert uinput.scroll(0, 0, diversion.RELEASE, source)
    assert uinput.scroll(0, 0, diversion.DEPRESS, source)
    mouse.write.assert_not_called()
    timeout_add.assert_not_called()
    source_remove.assert_not_called()


def test_scroll_repeat_observes_barriers_on_both_sides(scroll_input, monkeypatch):
    uinput, mouse, timeout_add, source_remove = scroll_input
    monkeypatch.setattr(diversion.time, "monotonic", lambda: 100)
    assert uinput.scroll(-1, 0, diversion.DEPRESS, (mock.Mock(receiver=None), 123, (-1, 0)))
    repeat = next(iter(uinput._scroll_repeats.values()))
    uinput.barrier(0.01, uinput.EventType.KEYBOARD)
    with mock.patch.object(diversion.time, "sleep") as sleep:
        assert not uinput._repeat_scroll(repeat)
        assert sleep.call_count == 1
        assert sleep.call_args.args[0] == pytest.approx(0.01)
        assert uinput.barrier_type == uinput.EventType.MOUSE
        uinput.key(diversion.evdev.ecodes.KEY_LEFTCTRL + 8, 0)
        assert sleep.call_count == 2


def test_equal_devices_and_same_direction_do_not_share_scroll_holds(scroll_input):
    uinput, mouse, timeout_add, source_remove = scroll_input
    first, second = mock.MagicMock(receiver=None), mock.MagicMock(receiver=None)
    first.__eq__.return_value = True
    second.__eq__.return_value = True
    assert uinput.scroll(-1, 0, diversion.DEPRESS, (first, 123, (-1, 0)))
    assert uinput.scroll(-1, 0, diversion.DEPRESS, (second, 123, (-1, 0)))
    assert uinput.scroll(-1, 0, diversion.DEPRESS, (first, 456, (-1, 0)))
    uinput.release_scroll(first, 123)
    assert len(uinput._scroll_repeats) == 2
    source_remove.assert_called_once_with(101)
    assert {r.source_id for r in uinput._scroll_repeats.values()} == {102, 103}


def test_physical_release_cancels_scroll_even_when_rule_no_longer_matches(scroll_input, monkeypatch):
    uinput, mouse, timeout_add, source_remove = scroll_input
    device = mock.Mock(receiver=None)
    assert uinput.scroll(-1, 0, diversion.DEPRESS, (device, 123, (-1, 0)))
    monkeypatch.setattr(diversion, "rules", mock.Mock())
    diversion.rules.evaluate.return_value = False
    diversion.evaluate_rules(None, None, device, (None, 123))
    assert not uinput._scroll_repeats
    source_remove.assert_called_once_with(101)
    assert uinput._scroll_keys == (None, None)


def test_queued_notifications_retain_their_scroll_control_snapshot(scroll_input, monkeypatch):
    uinput, mouse, timeout_add, source_remove = scroll_input
    device = mock.Mock(receiver=None)
    queued, observed = [], []
    monkeypatch.setattr(diversion.GLib, "idle_add", lambda callback, *args: queued.append((callback, args)))
    monkeypatch.setattr(diversion, "keys_down", ())
    monkeypatch.setattr(diversion, "rules", mock.Mock())
    diversion.rules.evaluate.side_effect = lambda *args: observed.append(uinput._scroll_keys)
    for data in (bytes.fromhex("007b000000000000"), bytes(8)):
        notification = HIDPPNotification(report_id=1, devnumber=1, sub_id=0x13, address=0, data=data)
        diversion.process_notification(device, notification, SupportedFeature.REPROG_CONTROLS_V4)
    for callback, args in queued:
        callback(*args)
    assert observed == [(123, None), (None, 123)]


@pytest.mark.parametrize("operation", ["reload", "save", "edit", "stop", "offline", "receiver_removed"])
def test_scroll_cleanup_on_lifecycle_boundaries(operation, scroll_input, monkeypatch, tmp_path):
    from solaar import listener
    from solaar.ui.diversion_rules import DiversionDialog

    uinput, mouse, timeout_add, source_remove = scroll_input
    receiver = mock.Mock()
    device = mock.Mock(receiver=receiver, online=False)
    assert uinput.scroll(-1, 0, diversion.DEPRESS, (device, 123, (-1, 0)))
    if operation == "reload":
        monkeypatch.setattr(diversion, "_file_path", str(tmp_path / "missing.yaml"))
        diversion.load_config_rule_file()
    elif operation == "save":
        assert diversion._save_config_rule_file(str(tmp_path / "rules.yaml"))
    elif operation == "edit":
        DiversionDialog.on_update(mock.Mock())
    elif operation == "stop":
        monkeypatch.setattr(listener, "_all_listeners", {})
        listener.stop_all()
    else:
        with mock.patch.object(diversion.GLib, "idle_add", side_effect=lambda callback, *args: callback(*args)):
            if operation == "offline":
                listener.SolaarListener._status_changed(mock.Mock(), device)
            else:
                state = mock.Mock(receiver=receiver)
                listener.SolaarListener.has_stopped(state)
    assert not uinput._scroll_repeats
    source_remove.assert_called_once_with(101)


def test_mouse_scroll_supports_click_depress_and_release_actions():
    click = diversion.MouseScroll([2, -1])
    depress = diversion.MouseScroll([[2, -1], diversion.DEPRESS])
    release = diversion.MouseScroll([[2, -1], diversion.RELEASE])

    assert click.action == diversion.CLICK
    assert click.data() == {"MouseScroll": [2, -1]}
    assert depress.action == diversion.DEPRESS
    assert depress.data() == {"MouseScroll": [[2, -1], diversion.DEPRESS]}
    assert release.action == diversion.RELEASE
    assert release.data() == {"MouseScroll": [[2, -1], diversion.RELEASE]}

    device = mock.Mock()
    with mock.patch.object(diversion.uinput, "scroll") as scroll:
        depress.evaluate(None, mock.Mock(), device, True)

    scroll.assert_called_once_with(2, -1, diversion.DEPRESS, (device, None, (2, -1)))


@pytest.mark.parametrize(
    "feature, data",
    [
        (
            SupportedFeature.REPROG_CONTROLS_V4,
            [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08],
        ),
        (SupportedFeature.GKEY, [0x01, 0x02, 0x03, 0x04]),
        (SupportedFeature.MKEYS, [0x01, 0x02, 0x03, 0x04]),
        (SupportedFeature.MR, [0x01, 0x02, 0x03, 0x04]),
        (SupportedFeature.THUMB_WHEEL, [0x01, 0x02, 0x03, 0x04, 0x05]),
        (SupportedFeature.DEVICE_UNIT_ID, [0x01, 0x02, 0x03, 0x04, 0x05]),
    ],
)
def test_process_notification(feature, data):
    device_mock = mock.Mock()
    notification = HIDPPNotification(
        report_id=0x01,
        devnumber=1,
        sub_id=0x13,
        address=0x00,
        data=bytes(data),
    )

    diversion.process_notification(device_mock, notification, feature)
