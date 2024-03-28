## Copyright (C) 2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
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

import pytest
import yaml

from logitech_receiver import common
from logitech_receiver import hidpp20
from logitech_receiver import hidpp20_constants
from logitech_receiver import special_keys

from . import hidpp

_hidpp20 = hidpp20.Hidpp20()

device_offline = hidpp.Device("REGISTERS", False)
device_registers = hidpp.Device("OFFLINE", True, 1.0)
device_nofeatures = hidpp.Device("NOFEATURES", True, 4.5)
device_zerofeatures = hidpp.Device("ZEROFEATURES", True, 4.5, [hidpp.Response("0000", 0x0000, "0001")])
device_broken = hidpp.Device("BROKEN", True, 4.5, [hidpp.Response("0500", 0x0000, "0001"), hidpp.Response(None, 0x0100)])
device_standard = hidpp.Device("STANDARD", True, 4.5, hidpp.r_keyboard_2)


@pytest.mark.parametrize(
    "device, expected_result, expected_count",
    [
        (device_offline, False, 0),
        (device_registers, False, 0),
        (device_nofeatures, False, 0),
        (device_zerofeatures, False, 0),
        (device_broken, False, 0),
        (device_standard, True, 9),
    ],
)
def test_FeaturesArray_check(device, expected_result, expected_count):
    featuresarray = hidpp20.FeaturesArray(device)

    result = featuresarray._check()
    result2 = featuresarray._check()

    assert result == expected_result
    assert result2 == expected_result
    assert (hidpp20_constants.FEATURE.ROOT in featuresarray) == expected_result
    assert len(featuresarray) == expected_count
    assert bool(featuresarray) == expected_result


@pytest.mark.parametrize(
    "device, expected0, expected1, expected2, expected5, expected5v",
    [
        (device_zerofeatures, None, None, None, None, None),
        (device_standard, 0x0000, 0x0001, 0x1000, hidpp20_constants.FEATURE.REPROG_CONTROLS_V4, 3),
    ],
)
def test_FeaturesArray_get_feature(device, expected0, expected1, expected2, expected5, expected5v):
    featuresarray = hidpp20.FeaturesArray(device)
    device.features = featuresarray

    result0 = featuresarray.get_feature(0)
    result1 = featuresarray.get_feature(1)
    result2 = featuresarray.get_feature(2)
    result5 = featuresarray.get_feature(5)
    result2r = featuresarray.get_feature(2)
    result5v = featuresarray.get_feature_version(hidpp20_constants.FEATURE.REPROG_CONTROLS_V4)

    assert result0 == expected0
    assert result1 == expected1
    assert result2 == expected2
    assert result2r == expected2
    assert result5 == expected5
    assert result5v == expected5v


@pytest.mark.parametrize(
    "device, expected_result",
    [
        (device_zerofeatures, []),
        (
            device_standard,
            [
                (hidpp20_constants.FEATURE.ROOT, 0),
                (hidpp20_constants.FEATURE.FEATURE_SET, 1),
                (hidpp20_constants.FEATURE.BATTERY_STATUS, 2),
                (hidpp20_constants.FEATURE.DEVICE_FW_VERSION, 3),
                (common.NamedInt(256, "unknown:0100"), 4),
                (hidpp20_constants.FEATURE.REPROG_CONTROLS_V4, 5),
                (None, 6),
                (None, 7),
                (None, 8),
            ],
        ),
    ],
)
def test_FeaturesArray_enumerate(device, expected_result):
    featuresarray = hidpp20.FeaturesArray(device)

    result = list(featuresarray.enumerate())

    assert result == expected_result


def test_FeaturesArray_setitem():
    featuresarray = hidpp20.FeaturesArray(device_standard)

    featuresarray[hidpp20_constants.FEATURE.ROOT] = 3
    featuresarray[hidpp20_constants.FEATURE.FEATURE_SET] = 5
    featuresarray[hidpp20_constants.FEATURE.FEATURE_SET] = 4

    assert featuresarray[hidpp20_constants.FEATURE.FEATURE_SET] == 4
    assert featuresarray.inverse[4] == hidpp20_constants.FEATURE.FEATURE_SET


def test_FeaturesArray_delitem():
    featuresarray = hidpp20.FeaturesArray(device_standard)

    with pytest.raises(ValueError):
        del featuresarray[5]


@pytest.mark.parametrize(
    "device, expected0, expected1, expected2, expected1v",
    [(device_zerofeatures, None, None, None, None), (device_standard, 0, 5, None, 3)],
)
def test_FeaturesArray_getitem(device, expected0, expected1, expected2, expected1v):
    featuresarray = hidpp20.FeaturesArray(device)
    device.features = featuresarray

    result_get0 = featuresarray[hidpp20_constants.FEATURE.ROOT]
    result_get1 = featuresarray[hidpp20_constants.FEATURE.REPROG_CONTROLS_V4]
    result_get2 = featuresarray[hidpp20_constants.FEATURE.GKEY]
    result_1v = featuresarray.get_feature_version(hidpp20_constants.FEATURE.REPROG_CONTROLS_V4)

    assert result_get0 == expected0
    assert result_get1 == expected1
    assert result_get2 == expected2
    assert result_1v == expected1v


@pytest.mark.parametrize(
    "device, index, cid, tid, flags, default_task, flag_names",
    [
        (device_standard, 2, 1, 1, 0x30, "Volume Up", ["reprogrammable", "divertable"]),
        (device_standard, 1, 2, 2, 0x20, "Volume Down", ["divertable"]),
    ],
)
def test_ReprogrammableKey_key(device, index, cid, tid, flags, default_task, flag_names):
    key = hidpp20.ReprogrammableKey(device, index, cid, tid, flags)

    assert key._device == device
    assert key.index == index
    assert key._cid == cid
    assert key._tid == tid
    assert key._flags == flags
    assert key.key == special_keys.CONTROL[cid]
    assert key.default_task == common.NamedInt(cid, default_task)
    assert list(key.flags) == flag_names


@pytest.mark.parametrize(
    "device, index, cid, tid, flags, pos, group, gmask, default_task, flag_names, group_names",
    [
        (device_standard, 2, 1, 1, 0x30, 0, 1, 3, "Volume Up", ["reprogrammable", "divertable"], ["g1", "g2"]),
        (device_standard, 1, 2, 2, 0x20, 1, 2, 1, "Volume Down", ["divertable"], ["g1"]),
    ],
)
def test_ReprogrammableKeyV4_key(device, index, cid, tid, flags, pos, group, gmask, default_task, flag_names, group_names):
    key = hidpp20.ReprogrammableKeyV4(device, index, cid, tid, flags, pos, group, gmask)

    assert key._device == device
    assert key.index == index
    assert key._cid == cid
    assert key._tid == tid
    assert key._flags == flags
    assert key.pos == pos
    assert key.group == group
    assert key._gmask == gmask
    assert key.key == special_keys.CONTROL[cid]
    assert key.default_task == common.NamedInt(cid, default_task)
    assert list(key.flags) == flag_names
    assert list(key.group_mask) == group_names


@pytest.mark.parametrize(
    "device, index", [(device_zerofeatures, -1), (device_zerofeatures, 5), (device_standard, -1), (device_standard, 6)]
)
def test_KeysArrayV4_query_key_indexerror(device, index):
    keysarray = hidpp20.KeysArrayV4(device, 5)

    with pytest.raises(IndexError):
        keysarray._query_key(index)


@pytest.mark.parametrize("device, index, cid", [(device_standard, 0, 0x0011), (device_standard, 4, 0x0003)])
def test_KeysArrayV4_query_key(device, index, cid):
    keysarray = hidpp20.KeysArrayV4(device, 5)

    keysarray._query_key(index)

    assert keysarray.keys[index]._cid == cid


@pytest.mark.parametrize(
    "device, count, index, cid, tid, flags, pos, group, gmask",
    [
        (device_standard, 4, 0, 0x0011, 0x0012, 0xCDAB, 1, 2, 3),
        (device_standard, 6, 1, 0x0111, 0x0022, 0xCDAB, 1, 2, 3),
        (device_standard, 8, 3, 0x0311, 0x0032, 0xCDAB, 1, 2, 4),
    ],
)
def test_KeysArrayV4__getitem(device, count, index, cid, tid, flags, pos, group, gmask):
    keysarray = hidpp20.KeysArrayV4(device, count)

    result = keysarray[index]

    assert result._device == device
    assert result.index == index
    assert result._cid == cid
    assert result._tid == tid
    assert result._flags == flags
    assert result.pos == pos
    assert result.group == group
    assert result._gmask == gmask


@pytest.mark.parametrize(
    "key, index", [(special_keys.CONTROL.Volume_Up, 2), (special_keys.CONTROL.Mute, 4), (special_keys.CONTROL.Next, None)]
)
def test_KeysArrayV4_index(key, index):
    keysarray = hidpp20.KeysArrayV4(device_standard, 7)

    result = keysarray.index(key)

    assert result == index


responses_key = [
    hidpp.Response("08", 0x0500),
    hidpp.Response("00500038010001010400000000000000", 0x0510, "00"),
    hidpp.Response("00510039010001010400000000000000", 0x0510, "01"),
    hidpp.Response("0052003A310003070500000000000000", 0x0510, "02"),
    hidpp.Response("0053003C310002030500000000000000", 0x0510, "03"),
    hidpp.Response("0056003E310002030500000000000000", 0x0510, "04"),
    hidpp.Response("00C300A9310003070500000000000000", 0x0510, "05"),
    hidpp.Response("00C4009D310003070500000000000000", 0x0510, "06"),
    hidpp.Response("00D700B4A00004000300000000000000", 0x0510, "07"),
    hidpp.Response("00500000000000000000000000000000", 0x0520, "0050"),
    hidpp.Response("00510000000000000000000000000000", 0x0520, "0051"),
    hidpp.Response("00520000500000000000000000000000", 0x0520, "0052"),
    hidpp.Response("00530000000000000000000000000000", 0x0520, "0053"),
    hidpp.Response("00560000000000000000000000000000", 0x0520, "0056"),
    hidpp.Response("00C30000000000000000000000000000", 0x0520, "00C3"),
    hidpp.Response("00C40000500000000000000000000000", 0x0520, "00C4"),
    hidpp.Response("00D70000510000000000000000000000", 0x0520, "00D7"),
]
device_key = hidpp.Device("KEY", responses=responses_key, feature=hidpp20_constants.FEATURE.REPROG_CONTROLS_V4, offset=5)


@pytest.mark.parametrize(
    "key, expected_index, expected_mapped_to, expected_remappable_to",
    [
        (
            special_keys.CONTROL.Left_Button,
            0,
            common.NamedInt(0x50, "Left Click"),
            [common.NamedInt(0x50, "Left Click"), common.NamedInt(0x51, "Right Click")],
        ),
        (
            special_keys.CONTROL.Right_Button,
            1,
            common.NamedInt(0x51, "Right Click"),
            [common.NamedInt(0x51, "Right Click"), common.NamedInt(0x50, "Left Click")],
        ),
        (special_keys.CONTROL.Middle_Button, 2, common.NamedInt(0x50, "Left Click"), None),
        (special_keys.CONTROL.Back_Button, 3, common.NamedInt(0x53, "Mouse Back Button"), None),
        (special_keys.CONTROL.Forward_Button, 4, common.NamedInt(0x56, "Mouse Forward Button"), None),
        (special_keys.CONTROL.Mouse_Gesture_Button, 5, common.NamedInt(0xC3, "Gesture Button Navigation"), None),
        (special_keys.CONTROL.Smart_Shift, 6, common.NamedInt(0x50, "Left Click"), None),
        (special_keys.CONTROL.Virtual_Gesture_Button, 7, common.NamedInt(0x51, "Right Click"), None),
    ],
)
def test_KeysArrayV4_key(key, expected_index, expected_mapped_to, expected_remappable_to):
    device_key._keys = _hidpp20.get_keys(device_key)
    device_key._keys._ensure_all_keys_queried()

    index = device_key._keys.index(key)
    mapped_to = device_key._keys[expected_index].mapped_to
    remappable_to = device_key._keys[expected_index].remappable_to

    assert index == expected_index
    assert mapped_to == expected_mapped_to
    if expected_remappable_to is not None:
        assert list(remappable_to) == expected_remappable_to


responses_remap = [
    hidpp.Response("0041", 0x0400),
    hidpp.Response("03", 0x0410),
    hidpp.Response("0301", 0x0410, "00"),
    hidpp.Response("0050", 0x0420, "00FF"),
    hidpp.Response("0050000200010001", 0x0430, "0050FF"),  # Left Button
    hidpp.Response("0051", 0x0420, "01FF"),
    hidpp.Response("0051000200010000", 0x0430, "0051FF"),  # Left Button
    hidpp.Response("0052", 0x0420, "02FF"),
    hidpp.Response("0052000100510000", 0x0430, "0052FF"),  # key DOWN
    hidpp.Response("050002", 0x0000, "1B04"),  # REPROGRAMMABLE_KEYS_V4
] + responses_key

device_remap = hidpp.Device("REMAP", responses=responses_remap, feature=hidpp20_constants.FEATURE.PERSISTENT_REMAPPABLE_ACTION)


@pytest.mark.parametrize(
    "key, expected_index, expected_mapped_to",
    [
        (special_keys.CONTROL.Left_Button, 0, common.NamedInt(0x01, "Mouse Button Left")),
        (special_keys.CONTROL.Right_Button, 1, common.NamedInt(0x01, "Mouse Button Left")),
        (special_keys.CONTROL.Middle_Button, 2, common.NamedInt(0x51, "DOWN")),
    ],
)
def test_KeysArrayPersistent_key(key, expected_index, expected_mapped_to):
    device_remap._remap_keys = _hidpp20.get_remap_keys(device_remap)
    device_remap._remap_keys._ensure_all_keys_queried()

    index = device_remap._remap_keys.index(key)
    mapped_to = device_remap._remap_keys[expected_index].remapped

    assert index == expected_index
    assert mapped_to == expected_mapped_to


# TODO SubParam, Gesture, Param, Gestures

responses_gestures = [
    hidpp.Response("4203410141020400320480148C21A301", 0x0400, "0000"),  # items
    hidpp.Response("A302A11EA30A4105822C852DAD2AAD2B", 0x0400, "0008"),
    hidpp.Response("8F408F418F434204AF54912282558264", 0x0400, "0010"),
    hidpp.Response("01000000000000000000000000000000", 0x0400, "0018"),
    hidpp.Response("6F000000000000000000000000000000", 0x0410, "0001FF"),  # item 0 enable
    hidpp.Response("01000000000000000000000000000000", 0x0410, "000101"),
    hidpp.Response("02000000000000000000000000000000", 0x0410, "000102"),
    hidpp.Response("04000000000000000000000000000000", 0x0410, "000104"),
    hidpp.Response("08000000000000000000000000000000", 0x0410, "000108"),
    hidpp.Response("00000000000000000000000000000000", 0x0410, "000110"),
    hidpp.Response("20000000000000000000000000000000", 0x0410, "000120"),
    hidpp.Response("40000000000000000000000000000000", 0x0410, "000140"),
    hidpp.Response("00000000000000000000000000000000", 0x0410, "000180"),
    hidpp.Response("00000000000000000000000000000000", 0x0410, "010101"),
    hidpp.Response("00000000000000000000000000000000", 0x0410, "010102"),
    hidpp.Response("04000000000000000000000000000000", 0x0410, "010104"),
    hidpp.Response("00000000000000000000000000000000", 0x0410, "010108"),
    hidpp.Response("04000000000000000000000000000000", 0x0410, "01010F"),
    hidpp.Response("00000000000000000000000000000000", 0x0430, "000101"),  # item 1 divert
    hidpp.Response("00000000000000000000000000000000", 0x0430, "000102"),
    hidpp.Response("00000000000000000000000000000000", 0x0430, "000104"),
    hidpp.Response("00000000000000000000000000000000", 0x0430, "000108"),
    hidpp.Response("00000000000000000000000000000000", 0x0430, "000110"),
    hidpp.Response("00000000000000000000000000000000", 0x0430, "000120"),
    hidpp.Response("00000000000000000000000000000000", 0x0430, "000140"),
    hidpp.Response("00000000000000000000000000000000", 0x0430, "000180"),
    hidpp.Response("00000000000000000000000000000000", 0x0430, "010101"),
    hidpp.Response("00000000000000000000000000000000", 0x0430, "010102"),
    hidpp.Response("00000000000000000000000000000000", 0x0430, "0001FF"),
    hidpp.Response("08000000000000000000000000000000", 0x0450, "03FF"),
    hidpp.Response("08000000000000000000000000000000", 0x0450, "01FF"),
    hidpp.Response("08000000000000000000000000000000", 0x0450, "02FF"),
    hidpp.Response("5C020000000000000000000000000000", 0x0450, "05FF"),
    hidpp.Response("00040000000000000000000000000000", 0x0450, "04FF"),
    hidpp.Response("01000000000000000000000000000000", 0x0460, "00FF"),
    hidpp.Response("01000000000000000000000000000000", 0x0470, "00FF"),
]
device_gestures = hidpp.Device("GESTURES", responses=responses_gestures, feature=hidpp20_constants.FEATURE.GESTURE_2)


def test_Gestures():
    gestures = _hidpp20.get_gestures(device_gestures)

    assert gestures
    assert len(gestures.gestures) == 17
    assert gestures.gestures[20].enabled() is None
    assert gestures.gestures[20].diverted() is None
    assert gestures.gestures[1].enabled() is True
    assert gestures.gestures[1].diverted() is False
    assert gestures.gestures[45].enabled() is False
    assert gestures.gestures[45].diverted() is None
    assert len(gestures.params) == 1
    assert gestures.params[4].value == 256
    assert gestures.params[4].default_value == 256

    print("SPEC", gestures.specs)
    assert len(gestures.specs) == 5
    assert gestures.specs[2].value == 8
    assert gestures.specs[4].value == 4


responses_backlight = [
    hidpp.Response("010118000001020003000400", 0x0400),
    hidpp.Response("0101FF00020003000400", 0x0410, "0101FF00020003000400"),
]

device_backlight = hidpp.Device("BACKLIGHT", responses=responses_backlight, feature=hidpp20_constants.FEATURE.BACKLIGHT2)


def test_Backlight():
    backlight = _hidpp20.get_backlight(device_backlight)
    result = backlight.write()

    assert backlight
    assert backlight.auto_supported
    assert backlight.temp_supported
    assert not backlight.perm_supported
    assert backlight.dho == 0x0002
    assert backlight.dhi == 0x0003
    assert backlight.dpow == 0x0004
    assert result is not None


@pytest.mark.parametrize(
    "hex, ID, color, speed, period, intensity, ramp, form",
    [
        ("FFFFFFFFFFFFFFFFFFFFFF", None, None, None, None, None, None, None),
        ("0000000000000000000000", common.NamedInt(0x0, "Disabled"), None, None, None, None, None, None),
        ("0120304010000000000000", common.NamedInt(0x1, "Static"), 0x203040, None, None, None, 0x10, None),
        ("0220304010000000000000", common.NamedInt(0x2, "Pulse"), 0x203040, 0x10, None, None, None, None),
        ("0800000000000000000000", common.NamedInt(0x8, "Boot"), None, None, None, None, None, None),
        ("0300000000005000000000", common.NamedInt(0x3, "Cycle"), None, None, 0x5000, 0x00, None, None),
        ("0A20304010005020000000", common.NamedInt(0xA, "Breathe"), 0x203040, None, 0x1000, 0x20, None, 0x50),
        ("0B20304000100000000000", common.NamedInt(0xB, "Ripple"), 0x203040, None, 0x1000, None, None, None),
    ],
)
def test_LEDEffectSetting(hex, ID, color, speed, period, intensity, ramp, form):
    byt = bytes.fromhex(hex)
    setting = hidpp20.LEDEffectSetting.from_bytes(byt)

    assert setting.ID == ID
    if ID is None:
        assert setting.bytes == byt
    else:
        assert getattr(setting, "color", None) == color
        assert getattr(setting, "speed", None) == speed
        assert getattr(setting, "period", None) == period
        assert getattr(setting, "intensity", None) == intensity
        assert getattr(setting, "ramp", None) == ramp
        assert getattr(setting, "form", None) == form
    assert setting.to_bytes() == byt


@pytest.mark.parametrize(
    "feature, function, response, ID, capabilities, period",
    [
        [hidpp20_constants.FEATURE.COLOR_LED_EFFECTS, 0x20, hidpp.Response("0102000300040005", 0x0420, "010200"), 3, 4, 5],
        [hidpp20_constants.FEATURE.COLOR_LED_EFFECTS, 0x20, hidpp.Response("0102000700080009", 0x0420, "010200"), 7, 8, 9],
    ],
)
def test_LEDEffectInfo(feature, function, response, ID, capabilities, period):
    device = hidpp.Device(feature=feature, responses=[response])

    info = hidpp20.LEDEffectInfo(feature, function, device, 1, 2)

    assert info.zindex == 1
    assert info.index == 2
    assert info.ID == ID
    assert info.capabilities == capabilities
    assert info.period == period


zone_responses_1 = [
    hidpp.Response("00000102", 0x0410, "00FF00"),
    hidpp.Response("0000000300040005", 0x0420, "000000"),
    hidpp.Response("0001000B00080009", 0x0420, "000100"),
]
zone_responses_2 = [
    hidpp.Response("0000000102", 0x0400, "00FF00"),
    hidpp.Response("0000000300040005", 0x0400, "000000"),
    hidpp.Response("0001000200080009", 0x0400, "000100"),
]


@pytest.mark.parametrize(
    "feature, function, offset, effect_function, responses, index, location, count, id_1",
    [
        [hidpp20_constants.FEATURE.COLOR_LED_EFFECTS, 0x10, 0, 0x20, zone_responses_1, 0, 1, 2, 0xB],
        [hidpp20_constants.FEATURE.RGB_EFFECTS, 0x00, 1, 0x00, zone_responses_2, 0, 1, 2, 2],
    ],
)
def test_LEDZoneInfo(feature, function, offset, effect_function, responses, index, location, count, id_1):
    device = hidpp.Device(feature=feature, responses=responses)

    zone = hidpp20.LEDZoneInfo(feature, function, offset, effect_function, device, index)

    assert zone.index == index
    assert zone.location == location
    assert zone.count == count
    assert len(zone.effects) == count
    assert zone.effects[1].ID == id_1


@pytest.mark.parametrize(
    "responses, setting, expected_command",
    [
        [zone_responses_1, hidpp20.LEDEffectSetting(ID=0), None],
        [zone_responses_1, hidpp20.LEDEffectSetting(ID=3, period=0x20, intensity=0x50), "000000000000000020500000"],
        [zone_responses_1, hidpp20.LEDEffectSetting(ID=0xB, color=0x808080, period=0x20), "000180808000002000000000"],
    ],
)
def test_LEDZoneInfo_to_command(responses, setting, expected_command):
    device = hidpp.Device(feature=hidpp20_constants.FEATURE.COLOR_LED_EFFECTS, responses=responses)
    zone = hidpp20.LEDZoneInfo(hidpp20_constants.FEATURE.COLOR_LED_EFFECTS, 0x10, 0, 0x20, device, 0)

    command = zone.to_command(setting)

    assert command == (bytes.fromhex(expected_command) if expected_command is not None else None)


effects_responses_1 = [hidpp.Response("0100000001", 0x0400)] + zone_responses_1
effects_responses_2 = [hidpp.Response("FFFF0100000001", 0x0400, "FFFF00")] + zone_responses_2


@pytest.mark.parametrize(
    "feature, cls, responses, readable, count, count_0",
    [
        [hidpp20_constants.FEATURE.COLOR_LED_EFFECTS, hidpp20.LEDEffectsInfo, effects_responses_1, 1, 1, 2],
        [hidpp20_constants.FEATURE.RGB_EFFECTS, hidpp20.RGBEffectsInfo, effects_responses_2, 1, 1, 2],
    ],
)
def test_LED_RGB_EffectsInfo(feature, cls, responses, readable, count, count_0):
    device = hidpp.Device(feature=feature, responses=responses)

    effects = cls(device)

    assert effects.readable == readable
    assert effects.count == count
    assert effects.zones[0].count == count_0


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
    #  eyaml = (
    #     "!LEDEffectSetting {ID: !NamedInt {name: Breathe, value: 0xa}, color: 0x10203, "
    #      "form: 0x4, intensity: 0x7, period: 0x50} "
    #  )

    setting = hidpp20.LEDEffectSetting.from_bytes(ebytes)

    assert setting.ID == 0x0A
    assert setting.color == 0x010203
    assert setting.period == 0x0050
    assert setting.form == 0x04
    assert setting.intensity == 0x07

    yaml_out = yaml.dump(setting)

    #    assert eyaml == re.compile(r"\s+").sub(" ", yaml_out)

    setting = yaml.safe_load(yaml_out)

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


responses_profiles = [
    hidpp.Response("0104010101020100FE0200", 0x0400),
    hidpp.Response("000101FF", 0x0450, "00000000"),
    hidpp.Response("FFFFFFFF", 0x0450, "00000004"),
    hidpp.Response("01010290018003000700140028FFFFFF", 0x0450, "00010000"),
    hidpp.Response("FFFF0000000000000000000000000000", 0x0450, "00010010"),
    hidpp.Response("8000FFFF900aFF00800204548000FFFF", 0x0450, "00010020"),
    hidpp.Response("900aFF00800204548000FFFF900aFF00", 0x0450, "00010030"),
    hidpp.Response("800204548000FFFF900aFF0080020454", 0x0450, "00010040"),
    hidpp.Response("8000FFFF900aFF00800204548000FFFF", 0x0450, "00010050"),
    hidpp.Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0450, "00010060"),
    hidpp.Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0450, "00010070"),
    hidpp.Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0450, "00010080"),
    hidpp.Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0450, "00010090"),
    hidpp.Response("54004500370000000000000000000000", 0x0450, "000100A0"),
    hidpp.Response("00000000000000000000000000000000", 0x0450, "000100B0"),
    hidpp.Response("00000000000000000000000000000000", 0x0450, "000100C0"),
    hidpp.Response("0A01020300500407000000FFFFFFFFFF", 0x0450, "000100D0"),
    hidpp.Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0450, "000100E0"),
    hidpp.Response("FFFFFFFFFFFFFFFFFFFFFFFFFF7C81", 0x0450, "000100EE"),
]

device_onb = hidpp.Device("ONB", True, 4.5, responses=responses_profiles, feature=hidpp20_constants.FEATURE.ONBOARD_PROFILES)


def test_profiles():
    device_onb._profiles = None
    profiles = _hidpp20.get_profiles(device_onb)

    assert profiles
