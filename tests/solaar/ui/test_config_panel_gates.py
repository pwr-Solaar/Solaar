from types import SimpleNamespace

from logitech_receiver.hidpp20_constants import SupportedFeature
from solaar.ui import config_panel


def _device(settings, persister):
    return SimpleNamespace(settings=settings, persister=persister)


def _setting(name, value, feature=None):
    return SimpleNamespace(name=name, _value=value, feature=feature)


def test_led_control_blocked_reads_setting_value_first():
    device = _device([_setting("led_control", False)], {"led_control": True})
    assert config_panel._led_control_blocked(device) is True

    device = _device([_setting("led_control", True)], {"led_control": False})
    assert config_panel._led_control_blocked(device) is False


def test_led_control_blocked_falls_back_to_persister():
    device = _device([_setting("led_control", None)], {"led_control": False})
    assert config_panel._led_control_blocked(device) is True


def test_led_control_blocked_unknown_does_not_block():
    device = _device([], {})
    assert config_panel._led_control_blocked(device) is False


def test_gate_blocks_rgb_zone_unaffected_by_led_control():
    # rgb_zone_ still keys off rgb_control, not led_control
    device = _device([_setting("led_control", False), _setting("rgb_control", True), _setting("rgb_zone_1", None)], {})
    assert config_panel._gate_blocks(device, "rgb_zone_1") is False


def test_gate_blocks_perkey_v1_follows_led_control():
    # 0x8080 per-key pairs with 0x8070 zones — gates on led_control
    perkey_v1 = _setting("per-key-lighting", None, feature=SupportedFeature.PER_KEY_LIGHTING)
    off = _device([_setting("led_control", False), perkey_v1], {})
    assert config_panel._gate_blocks(off, "per-key-lighting") is True

    on = _device([_setting("led_control", True), perkey_v1], {})
    assert config_panel._gate_blocks(on, "per-key-lighting") is False


def test_gate_blocks_perkey_v2_ignores_led_control():
    # 0x8081 per-key keeps gating on rgb_control + zone-Static
    perkey_v2 = _setting("per-key-lighting", None, feature=SupportedFeature.PER_KEY_LIGHTING_V2)
    device = _device([_setting("led_control", False), _setting("rgb_control", True), perkey_v2], {})
    assert config_panel._gate_blocks(device, "per-key-lighting") is False
