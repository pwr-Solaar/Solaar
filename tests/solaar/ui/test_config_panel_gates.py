from types import SimpleNamespace

from solaar.ui import config_panel


def _device(settings, persister):
    return SimpleNamespace(settings=settings, persister=persister)


def _setting(name, value):
    return SimpleNamespace(name=name, _value=value)


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


def test_gate_blocks_led_zone_follows_led_control():
    off = _device([_setting("led_control", False), _setting("led_zone_1", None)], {})
    assert config_panel._gate_blocks(off, "led_zone_1") is True

    on = _device([_setting("led_control", True), _setting("led_zone_1", None)], {})
    assert config_panel._gate_blocks(on, "led_zone_1") is False


def test_gate_blocks_rgb_zone_unaffected_by_led_control():
    # rgb_zone_ still keys off rgb_control, not led_control
    device = _device([_setting("led_control", False), _setting("rgb_control", True), _setting("rgb_zone_1", None)], {})
    assert config_panel._gate_blocks(device, "rgb_zone_1") is False
