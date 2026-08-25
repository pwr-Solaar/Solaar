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


G915_TKL = "B35F408EC343"


def _gkey_block(built_in):
    """The generated G-key -> F-key block of a built_in_rules tree."""
    return built_in.components[1]


def _fake_device(model_id=G915_TKL, divert=None):
    device = mock.Mock()
    device.modelId = model_id
    if divert is None:
        device.settings = []
    else:
        setting = mock.Mock()
        setting.name = "divert-gkeys"
        setting._value = divert
        device.settings = [setting]
    return device


def test_built_in_gkey_rules_cover_the_whole_f_row():
    block = _gkey_block(diversion._build_built_in_rules())

    assert isinstance(block.components[0], diversion.GKeysAreFKeys)
    assert len(block.components) == 1 + 2 * 12  # gate + press/release per key

    first = block.components[1]
    assert [type(c) for c in first.components] == [diversion.GKeysAreFKeys, diversion.Key, diversion.KeyPress]
    assert first.components[1].key == diversion.CONTROL.G1
    assert first.components[1].action == diversion.Key.DOWN
    assert first.components[2].key_names == ["F1"]
    assert first.components[2].action == diversion.DEPRESS

    last = block.components[-1]
    assert last.components[1].key == diversion.CONTROL.G12
    assert last.components[1].action == diversion.Key.UP
    assert last.components[2].key_names == ["F12"]
    assert last.components[2].action == diversion.RELEASE


def test_built_in_gkey_rules_yield_per_key():
    block = _gkey_block(diversion._build_built_in_rules({5, 12}))

    mapped = {c.components[1].key for c in block.components[1:]}
    assert diversion.CONTROL.G5 not in mapped
    assert diversion.CONTROL.G12 not in mapped
    # remapping one key must not cost the rest of the row
    assert diversion.CONTROL.G1 in mapped
    assert diversion.CONTROL.G11 in mapped
    assert len(block.components) == 1 + 2 * 10


def test_gkeys_are_fkeys_condition_is_per_device():
    notification = mock.Mock()
    gate = diversion.GKeysAreFKeys(1)

    assert gate.evaluate(SupportedFeature.GKEY, notification, _fake_device(), True) is True
    assert gate.evaluate(SupportedFeature.GKEY, notification, _fake_device("000000000A78"), True) is False


def test_gkeys_are_fkeys_condition_respects_row_length():
    notification = mock.Mock()
    device = _fake_device()

    assert diversion.GKeysAreFKeys(12).evaluate(SupportedFeature.GKEY, notification, device, True) is True
    # a 13th G-key on such a model would be a macro key, not part of the F-row
    assert diversion.GKeysAreFKeys(13).evaluate(SupportedFeature.GKEY, notification, device, True) is False


def test_gkeys_are_fkeys_condition_is_not_user_writable():
    assert "GKeysAreFKeys" not in diversion.COMPONENTS


def test_overridden_gkeys_finds_nested_keys():
    rule = diversion.Rule(
        [
            {"Rule": [{"Key": ["G3", "pressed"]}, {"KeyPress": "a"}]},
            {"Rule": [{"Not": {"KeyIsDown": "G7"}}, {"KeyPress": "b"}]},
            {"Rule": [{"Or": [{"Key": ["G9", "released"]}, {"Key": ["M1", "pressed"]}]}, {"KeyPress": "c"}]},
            {"Rule": [{"Key": ["Brightness Up", "pressed"]}, {"KeyPress": "d"}]},
        ]
    )

    assert diversion._overridden_gkeys(rule) == {3, 7, 9}


def test_overridden_gkeys_of_rules_without_gkeys():
    rule = diversion.Rule([{"Rule": [{"Key": ["Brightness Up", "pressed"]}, {"KeyPress": "d"}]}])

    assert diversion._overridden_gkeys(rule) == set()


@pytest.mark.parametrize(
    "feature, model_id, divert, expected",
    [
        (SupportedFeature.GKEY, G915_TKL, False, True),  # switch off: built-ins own the row
        (SupportedFeature.GKEY, G915_TKL, True, False),  # switch on: user rules see the keys
        (SupportedFeature.GKEY, G915_TKL, None, True),  # no setting yet, default to F-keys
        (SupportedFeature.GKEY, "000000000A78", False, False),  # other keyboards are untouched
        (SupportedFeature.MKEYS, G915_TKL, False, False),  # only G-keys are remapped
    ],
)
def test_gkeys_owned_by_built_ins(feature, model_id, divert, expected):
    device = _fake_device(model_id, divert)

    assert diversion._gkeys_owned_by_built_ins(feature, device) is expected


def test_evaluate_rules_skips_user_rules_when_built_ins_own_the_row():
    device = _fake_device(divert=False)
    notification = mock.Mock()

    with mock.patch.object(diversion, "rules") as user_rules:
        with mock.patch.object(diversion, "built_in_rules") as built_ins:
            diversion.evaluate_rules(SupportedFeature.GKEY, notification, device)

    user_rules.evaluate.assert_not_called()
    built_ins.evaluate.assert_called_once()


def test_evaluate_rules_uses_all_rules_otherwise():
    device = _fake_device(divert=True)
    notification = mock.Mock()

    with mock.patch.object(diversion, "rules") as user_rules:
        diversion.evaluate_rules(SupportedFeature.GKEY, notification, device)

    user_rules.evaluate.assert_called_once()


def test_uinput_writable(monkeypatch):
    monkeypatch.setattr(diversion, "evdev", object())
    monkeypatch.setattr(diversion.os, "access", lambda path, mode: path == diversion._UINPUT_PATH)
    assert diversion.uinput_writable() is True

    monkeypatch.setattr(diversion.os, "access", lambda path, mode: False)
    assert diversion.uinput_writable() is False

    monkeypatch.setattr(diversion, "evdev", None)
    assert diversion.uinput_writable() is False
