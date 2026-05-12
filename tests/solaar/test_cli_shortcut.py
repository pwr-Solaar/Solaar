from unittest import mock

from logitech_receiver import diversion
from logitech_receiver import diversion_shortcuts
from logitech_receiver.special_keys import CONTROL


def test_normalize_smart_shift_alias():
    assert diversion_shortcuts.normalize_key_name("smart-shift") == CONTROL["Smart Shift"]
    assert diversion_shortcuts.normalize_key_name("Smart Shift") == CONTROL["Smart Shift"]


def test_parse_shortcut():
    assert diversion_shortcuts.parse_shortcut("XF86AudioPlay") == "XF86AudioPlay"
    assert diversion_shortcuts.parse_shortcut("Control_L+Alt_L+T") == ["Control_L", "Alt_L", "T"]


def test_set_shortcut_rule_creates_user_rule(tmp_path):
    rules_file = tmp_path / "rules.yaml"
    original_rules = diversion.rules
    original_file_path = diversion._file_path
    try:
        diversion.rules = diversion.built_in_rules
        diversion._file_path = str(rules_file)
        with mock.patch("logitech_receiver.diversion.load_config_rule_file"):
            rule = diversion_shortcuts.set_shortcut_rule(CONTROL["Smart Shift"], "Control_L+Alt_L+T")

        assert rules_file.exists()
        assert rule.components[0].data() == {"Key": ["Smart Shift", "pressed"]}
        assert rule.components[1].data() == {"KeyPress": [["Control_L", "Alt_L", "T"], "click"]}
        assert diversion.rules.components[0].source == str(rules_file)
    finally:
        diversion.rules = original_rules
        diversion._file_path = original_file_path


def test_set_shortcut_rule_replaces_existing_rule(tmp_path):
    rules_file = tmp_path / "rules.yaml"
    original_rules = diversion.rules
    original_file_path = diversion._file_path
    try:
        diversion._file_path = str(rules_file)
        diversion.rules = diversion.Rule(
            [
                diversion.Rule(
                    [
                        diversion.Rule(
                            [
                                {"Key": ["Smart Shift", "pressed"]},
                                {"KeyPress": [["Control_L", "Alt_L", "T"], "click"]},
                            ]
                        )
                    ],
                    source=str(rules_file),
                )
            ]
        )
        with mock.patch("logitech_receiver.diversion.load_config_rule_file"):
            diversion_shortcuts.set_shortcut_rule(CONTROL["Smart Shift"], "Super_L+space")

        user_rules = diversion.rules.components[0]
        assert len(user_rules.components) == 1
        assert user_rules.components[0].components[1].data() == {"KeyPress": [["Super_L", "space"], "click"]}
    finally:
        diversion.rules = original_rules
        diversion._file_path = original_file_path
