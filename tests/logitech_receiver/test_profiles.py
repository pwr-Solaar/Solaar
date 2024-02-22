import re

import logitech_receiver.hidpp20 as hidpp20
import pytest
import yaml


def test_led_setting_bytes():
    ebytes = bytes.fromhex("0A01020300500407000000")

    setting = hidpp20.LEDEffectSetting.from_bytes(ebytes)

    assert setting.ID == 0x0A
    assert setting.color == 0x010203
    assert setting.period == 0x0050
    assert setting.form == 0x04
    assert setting.intensity == 0x07

    bytes_out = setting.to_bytes()

    assert ebytes == bytes_out


def test_led_setting_yaml():
    ebytes = bytes.fromhex("0A01020300500407000000")
    eyaml = (
        "!LEDEffectSetting {ID: !NamedInt {name: Breathe, value: 0xa}, color: 0x10203, "
        "form: 0x4, intensity: 0x7, period: 0x50} "
    )

    setting = hidpp20.LEDEffectSetting.from_bytes(ebytes)

    assert setting.ID == 0x0A
    assert setting.color == 0x010203
    assert setting.period == 0x0050
    assert setting.form == 0x04
    assert setting.intensity == 0x07

    yaml_out = yaml.dump(setting)

    assert eyaml == re.compile(r"\s+").sub(" ", yaml_out)

    setting = yaml.safe_load(eyaml)

    assert setting.to_bytes() == ebytes


def test_button_bytes_1():
    bbytes = bytes.fromhex("8000FFFF")

    button = hidpp20.Button.from_bytes(bbytes)

    assert button.behavior == 0x8
    assert button.type == 0x00

    bytes_out = button.to_bytes()

    assert bbytes == bytes_out


def test_button_bytes_2():
    bbytes = bytes.fromhex("900aFF00")

    button = hidpp20.Button.from_bytes(bbytes)

    assert button.behavior == 0x9

    bytes_out = button.to_bytes()

    assert bbytes == bytes_out


def test_button_bytes_3():
    bbytes = bytes.fromhex("80020454")

    button = hidpp20.Button.from_bytes(bbytes)

    assert button.behavior == 0x8
    assert button.modifiers == 0x04

    bytes_out = button.to_bytes()

    assert bbytes == bytes_out


@pytest.fixture
def profile_bytes():
    return bytes.fromhex(
        "01010290018003000700140028FFFFFF"
        "FFFF0000000000000000000000000000"
        "8000FFFF900aFF00800204548000FFFF"
        "900aFF00800204548000FFFF900aFF00"
        "800204548000FFFF900aFF0080020454"
        "8000FFFF900aFF00800204548000FFFF"
        "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
        "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
        "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
        "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
        "54004500370000000000000000000000"
        "00000000000000000000000000000000"
        "00000000000000000000000000000000"
        "0A01020300500407000000FFFFFFFFFF"
        "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
        "FFFFFFFFFFFFFFFFFFFFFFFFFF7C81"
    )


def test_profile_bytes(profile_bytes):
    pbytes = profile_bytes
    profile = hidpp20.OnboardProfile.from_bytes(2, 1, 16, 0, pbytes)

    assert profile.sector == 2
    assert profile.resolutions == [0x0190, 0x0380, 0x0700, 0x1400, 0x2800]
    assert profile.buttons[0].to_bytes() == bytes.fromhex("8000FFFF")
    assert profile.lighting[0].to_bytes() == bytes.fromhex("0A01020300500407000000")
    assert profile.name == "TE7"

    bytes_out = profile.to_bytes(255)

    assert pbytes == bytes_out
