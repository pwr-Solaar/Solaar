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
from logitech_receiver import exceptions
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
        (device_standard, 0x0000, 0x0001, 0x0020, hidpp20_constants.FEATURE.REPROG_CONTROLS_V4, 3),
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
                (hidpp20_constants.FEATURE.CONFIG_CHANGE, 2),
                (hidpp20_constants.FEATURE.DEVICE_FW_VERSION, 3),
                (common.NamedInt(256, "unknown:0100"), 4),
                (hidpp20_constants.FEATURE.REPROG_CONTROLS_V4, 5),
                (None, 6),
                (None, 7),
                (hidpp20_constants.FEATURE.BATTERY_STATUS, 8),
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
        (device_standard, 1, 0x51, 0x39, 0x60, 0, 1, 1, "Right Click", ["divertable", "persistently divertable"], ["g1"]),
        (device_standard, 2, 0x52, 0x3A, 0x11, 1, 2, 3, "Mouse Middle Button", ["mse", "reprogrammable"], ["g1", "g2"]),
        (
            device_standard,
            3,
            0x53,
            0x3C,
            0x110,
            2,
            2,
            7,
            "Mouse Back Button",
            ["reprogrammable", "raw XY"],
            ["g1", "g2", "g3"],
        ),
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
    "responses, index, mapped_to, remappable_to, mapping_flags",
    [
        (hidpp.responses_key, 1, "Right Click", common.UnsortedNamedInts(Right_Click=81, Left_Click=80), []),
        (hidpp.responses_key, 2, "Left Click", None, ["diverted"]),
        (hidpp.responses_key, 3, "Mouse Back Button", None, ["diverted", "persistently diverted"]),
        (hidpp.responses_key, 4, "Mouse Forward Button", None, ["diverted", "raw XY diverted"]),
    ],
)
# these fields need access all the key data, so start by setting up a device and its key data
def test_ReprogrammableKeyV4_query(responses, index, mapped_to, remappable_to, mapping_flags):
    device = hidpp.Device("KEY", responses=responses, feature=hidpp20_constants.FEATURE.REPROG_CONTROLS_V4, offset=5)
    device._keys = _hidpp20.get_keys(device)

    key = device.keys[index]

    assert key.mapped_to == mapped_to
    assert (key.remappable_to == remappable_to) or remappable_to is None
    assert list(key.mapping_flags) == mapping_flags


@pytest.mark.parametrize(
    "responses, index, diverted, persistently_diverted, rawXY_reporting, remap, sets",
    [
        (hidpp.responses_key, 1, True, False, True, 0x52, ["0051080000"]),
        (hidpp.responses_key, 2, False, True, False, 0x51, ["0052020000", "0052200000", "0052000051"]),
        (hidpp.responses_key, 3, False, True, True, 0x50, ["0053020000", "00530C0000", "0053300000", "0053000050"]),
        (hidpp.responses_key, 4, False, False, False, 0x50, ["0056020000", "0056080000", "0056200000", "0056000050"]),
    ],
)
def test_ReprogrammableKeyV4_set(responses, index, diverted, persistently_diverted, rawXY_reporting, remap, sets, mocker):
    responses += [hidpp.Response(r, 0x530, r) for r in sets]
    device = hidpp.Device("KEY", responses=responses, feature=hidpp20_constants.FEATURE.REPROG_CONTROLS_V4, offset=5)
    device._keys = _hidpp20.get_keys(device)
    device._keys._ensure_all_keys_queried()  # do this now so that the last requests are sets
    spy_request = mocker.spy(device, "request")

    key = device.keys[index]
    _mapping_flags = list(key.mapping_flags)

    if "divertable" in key.flags or not diverted:
        key.set_diverted(diverted)
    else:
        with pytest.raises(exceptions.FeatureNotSupported):
            key.set_diverted(diverted)
    assert ("diverted" in list(key.mapping_flags)) == (diverted and "divertable" in key.flags)

    if "persistently divertable" in key.flags or not persistently_diverted:
        key.set_persistently_diverted(persistently_diverted)
    else:
        with pytest.raises(exceptions.FeatureNotSupported):
            key.set_persistently_diverted(persistently_diverted)
    assert ("persistently diverted" in key.mapping_flags) == (persistently_diverted and "persistently divertable" in key.flags)

    if "raw XY" in key.flags or not rawXY_reporting:
        key.set_rawXY_reporting(rawXY_reporting)
    else:
        with pytest.raises(exceptions.FeatureNotSupported):
            key.set_rawXY_reporting(rawXY_reporting)
    assert ("raw XY diverted" in list(key.mapping_flags)) == (rawXY_reporting and "raw XY" in key.flags)

    if remap in key.remappable_to or remap == 0:
        key.remap(remap)
    else:
        with pytest.raises(exceptions.FeatureNotSupported):
            key.remap(remap)
    assert (key.mapped_to == remap) or (remap not in key.remappable_to and remap != 0)

    hidpp.match_requests(len(sets), responses, spy_request.call_args_list)


@pytest.mark.parametrize(
    "r, index, cid, actionId, remapped, mask, status, action, modifiers, byts, remap",
    [
        (hidpp.responses_key, 1, 0x0051, 0x02, 0x0002, 0x01, 0, "Mouse Button: 2", "Cntrl+", "02000201", "01000400"),
        (hidpp.responses_key, 2, 0x0052, 0x01, 0x0001, 0x00, 1, "Key: 1", "", "01000100", "02005004"),
        (hidpp.responses_key, 3, 0x0053, 0x02, 0x0001, 0x00, 1, "Mouse Button: 1", "", "02000100", "7FFFFFFF"),
    ],
)
def test_RemappableAction(r, index, cid, actionId, remapped, mask, status, action, modifiers, byts, remap, mocker):
    if int(remap, 16) == special_keys.KEYS_Default:
        responses = r + [hidpp.Response("040000", 0x0000, "1C00"), hidpp.Response("00", 0x450, f"{cid:04X}" + "FF")]
    else:
        responses = r + [hidpp.Response("040000", 0x0000, "1C00"), hidpp.Response("00", 0x440, f"{cid:04X}" + "FF" + remap)]
    device = hidpp.Device("KEY", responses=responses, feature=hidpp20_constants.FEATURE.REPROG_CONTROLS_V4, offset=5)
    key = hidpp20.PersistentRemappableAction(device, index, cid, actionId, remapped, mask, status)
    spy_request = mocker.spy(device, "request")

    assert key._device == device
    assert key.index == index
    assert key._cid == cid
    assert key.actionId == actionId
    assert key.remapped == remapped
    assert key._modifierMask == mask
    assert key.cidStatus == status
    assert key.key == special_keys.CONTROL[cid]
    assert key.actionType == special_keys.ACTIONID[actionId]
    assert key.action == action
    assert key.modifiers == modifiers
    assert key.data_bytes.hex().upper() == byts

    key.remap(bytes.fromhex(remap))
    assert key.data_bytes.hex().upper() == (byts if int(remap, 16) == special_keys.KEYS_Default else remap)

    if int(remap, 16) != special_keys.KEYS_Default:
        hidpp.match_requests(1, responses, spy_request.call_args_list)


# KeysArray methods tested in KeysArrayV4

# KeysArrayV2 not tested as there is no documentation


@pytest.mark.parametrize(
    "device, index", [(device_zerofeatures, -1), (device_zerofeatures, 5), (device_standard, -1), (device_standard, 6)]
)
def test_KeysArrayV4_index_error(device, index):
    keysarray = hidpp20.KeysArrayV4(device, 5)

    with pytest.raises(IndexError):
        keysarray[index]

    with pytest.raises(IndexError):
        keysarray._query_key(index)


@pytest.mark.parametrize("device, index, top, cid", [(device_standard, 0, 2, 0x0011), (device_standard, 4, 5, 0x0003)])
def test_KeysArrayV4_query_key(device, index, top, cid):
    keysarray = hidpp20.KeysArrayV4(device, 5)

    keysarray._query_key(index)

    assert keysarray.keys[index]._cid == cid
    assert len(keysarray[index:top]) == top - index
    assert len(list(keysarray)) == 5


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


device_key = hidpp.Device("KEY", responses=hidpp.responses_key, feature=hidpp20_constants.FEATURE.REPROG_CONTROLS_V4, offset=5)


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


@pytest.mark.parametrize(
    "device, index", [(device_zerofeatures, -1), (device_zerofeatures, 5), (device_standard, -1), (device_standard, 6)]
)
def test_KeysArrayPersistent_index_error(device, index):
    keysarray = hidpp20.KeysArrayPersistent(device, 5)

    with pytest.raises(IndexError):
        keysarray[index]

    with pytest.raises(IndexError):
        keysarray._query_key(index)


@pytest.mark.parametrize(
    "responses, key, index, mapped_to, capabilities",
    [
        (hidpp.responses_remap, special_keys.CONTROL.Left_Button, 0, common.NamedInt(0x01, "Mouse Button Left"), 0x41),
        (hidpp.responses_remap, special_keys.CONTROL.Right_Button, 1, common.NamedInt(0x01, "Mouse Button Left"), 0x41),
        (hidpp.responses_remap, special_keys.CONTROL.Middle_Button, 2, common.NamedInt(0x51, "DOWN"), 0x41),
    ],
)
def test_KeysArrayPersistent_key(responses, key, index, mapped_to, capabilities):
    device = hidpp.Device("REMAP", responses=responses, feature=hidpp20_constants.FEATURE.PERSISTENT_REMAPPABLE_ACTION)
    device._remap_keys = _hidpp20.get_remap_keys(device)
    device._remap_keys._ensure_all_keys_queried()

    assert device._remap_keys.index(key) == index
    assert device._remap_keys[index].remapped == mapped_to
    assert device._remap_keys.capabilities == capabilities


@pytest.mark.parametrize(
    "id, length, minimum, maximum, widget, min, max, wid, string",
    [
        ("left", 1, 5, 8, "Widget", 5, 8, "Widget", "left"),
        ("left", 1, None, None, None, 0, 255, "Scale", "left"),
    ],
)
def test_SubParam(id, length, minimum, maximum, widget, min, max, wid, string):
    subparam = hidpp20.SubParam(id, length, minimum, maximum, widget)

    assert subparam.id == id
    assert subparam.length == length
    assert subparam.minimum == min
    assert subparam.maximum == max
    assert subparam.widget == wid
    assert subparam.__str__() == string
    assert subparam.__repr__() == string


@pytest.mark.parametrize(
    "device, low, high, next_index, next_diversion_index, name, cbe, si, sdi, eom, dom",
    [
        (device_standard, 0x01, 0x01, 5, 10, "Tap1Finger", True, 5, None, (0, 0x20), (None, None)),
        (device_standard, 0x03, 0x02, 6, 11, "Tap3Finger", False, None, 11, (None, None), (1, 0x08)),
    ],
)
def test_Gesture(device, low, high, next_index, next_diversion_index, name, cbe, si, sdi, eom, dom):
    gesture = hidpp20.Gesture(device, low, high, next_index, next_diversion_index)

    assert gesture._device == device
    assert gesture.id == low
    assert gesture.gesture == name
    assert gesture.can_be_enabled == cbe
    assert gesture.can_be_enabled == cbe
    assert gesture.index == si
    assert gesture.diversion_index == sdi
    assert gesture.enable_offset_mask() == eom
    assert gesture.diversion_offset_mask() == dom
    assert gesture.as_int() == low
    assert int(gesture) == low


@pytest.mark.parametrize(
    "responses, gest, enabled, diverted, set_result, unset_result, divert_result, undivert_result",
    [
        (hidpp.responses_gestures, 20, None, None, None, None, None, None),
        (hidpp.responses_gestures, 1, True, False, "01", "00", "01", "00"),
        (hidpp.responses_gestures, 45, False, None, "01", "00", None, None),
    ],
)
def test_Gesture_set(responses, gest, enabled, diverted, set_result, unset_result, divert_result, undivert_result):
    device = hidpp.Device("GESTURE", responses=responses, feature=hidpp20_constants.FEATURE.GESTURE_2)
    gestures = _hidpp20.get_gestures(device)

    gesture = gestures.gesture(gest)

    assert gesture.enabled() == enabled
    assert gesture.diverted() == diverted
    assert gesture.set(True) == (bytes.fromhex(set_result) if set_result is not None else None)
    assert gesture.set(False) == (bytes.fromhex(unset_result) if unset_result is not None else None)
    assert gesture.divert(True) == (bytes.fromhex(divert_result) if divert_result is not None else None)
    assert gesture.divert(False) == (bytes.fromhex(undivert_result) if undivert_result is not None else None)


@pytest.mark.parametrize(
    "responses, prm, id, index, size, value, default_value, write1, write2",
    [
        (hidpp.responses_gestures, 4, common.NamedInt(4, "ScaleFactor"), 0, 2, 256, 256, "0080", "0180"),
    ],
)
def test_Param(responses, prm, id, index, size, value, default_value, write1, write2):
    device = hidpp.Device("GESTURE", responses=responses, feature=hidpp20_constants.FEATURE.GESTURE_2)
    gestures = _hidpp20.get_gestures(device)

    param = gestures.param(prm)

    assert param.id == id
    assert param.index == index
    assert param.size == size
    assert param.value == value
    assert param.default_value == default_value
    assert str(param) == id
    assert int(param) == id
    assert param.write(bytes.fromhex(write1)).hex().upper() == f"{index:02X}" + write1 + "FF"
    assert param.write(bytes.fromhex(write2)).hex().upper() == f"{index:02X}" + write2 + "FF"


@pytest.mark.parametrize(
    "responses, id, s, byte_count, value, string",
    [
        (hidpp.responses_gestures, 1, "DVI field width", 1, 8, "[DVI field width=8]"),
        (hidpp.responses_gestures, 2, "field widths", 1, 8, "[field widths=8]"),
        (hidpp.responses_gestures, 3, "period unit", 2, 2048, "[period unit=2048]"),
    ],
)
def test_Spec(responses, id, s, byte_count, value, string):
    device = hidpp.Device("GESTURE", responses=responses, feature=hidpp20_constants.FEATURE.GESTURE_2)
    gestures = _hidpp20.get_gestures(device)

    spec = gestures.specs[id]

    assert spec.id == id
    assert spec.spec == s
    assert spec.byte_count == byte_count
    assert spec.value == value
    assert repr(spec) == string


def test_Gestures():
    device = hidpp.Device("GESTURES", responses=hidpp.responses_gestures, feature=hidpp20_constants.FEATURE.GESTURE_2)
    gestures = _hidpp20.get_gestures(device)

    assert gestures

    assert len(gestures.gestures) == 17
    assert gestures.gesture(20) == gestures.gestures[20]
    assert gestures.gesture_enabled(20) is None
    assert gestures.gesture_enabled(1) is True
    assert gestures.gesture_enabled(45) is False
    assert gestures.enable_gesture(20) is None
    assert gestures.enable_gesture(45) == bytes.fromhex("01")
    assert gestures.disable_gesture(20) is None
    assert gestures.disable_gesture(45) == bytes.fromhex("00")

    assert len(gestures.params) == 1
    assert gestures.param(4) == gestures.params[4]
    assert gestures.get_param(4) == 256
    assert gestures.set_param(4, 128) is None

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
        ("0A01020300500407000000", common.NamedInt(0xA, "Breathe"), 0x010203, None, 0x0050, 0x07, None, 0x04),
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
    assert yaml.safe_load(yaml.dump(setting)) == setting
    assert yaml.safe_load(str(setting)) == setting


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


@pytest.mark.parametrize(
    "feature, function, offset, effect_function, responses, index, location, count, id_1",
    [
        [hidpp20_constants.FEATURE.COLOR_LED_EFFECTS, 0x10, 0, 0x20, hidpp.zone_responses_1, 0, 1, 2, 0xB],
        [hidpp20_constants.FEATURE.RGB_EFFECTS, 0x00, 1, 0x00, hidpp.zone_responses_2, 0, 1, 2, 2],
    ],
)
def test_LEDZoneInfo(feature, function, offset, effect_function, responses, index, location, count, id_1):
    device = hidpp.Device(feature=feature, responses=responses, offset=0x07)

    zone = hidpp20.LEDZoneInfo(feature, function, offset, effect_function, device, index)

    assert zone.index == index
    assert zone.location == location
    assert zone.count == count
    assert len(zone.effects) == count
    assert zone.effects[1].ID == id_1


@pytest.mark.parametrize(
    "responses, setting, expected_command",
    [
        [hidpp.zone_responses_1, hidpp20.LEDEffectSetting(ID=0), None],
        [hidpp.zone_responses_1, hidpp20.LEDEffectSetting(ID=3, period=0x20, intensity=0x50), "000000000000000020500000"],
        [hidpp.zone_responses_1, hidpp20.LEDEffectSetting(ID=0xB, color=0x808080, period=0x20), "000180808000002000000000"],
    ],
)
def test_LEDZoneInfo_to_command(responses, setting, expected_command):
    device = hidpp.Device(feature=hidpp20_constants.FEATURE.COLOR_LED_EFFECTS, responses=responses, offset=0x07)
    zone = hidpp20.LEDZoneInfo(hidpp20_constants.FEATURE.COLOR_LED_EFFECTS, 0x10, 0, 0x20, device, 0)

    command = zone.to_command(setting)

    assert command == (bytes.fromhex(expected_command) if expected_command is not None else None)


@pytest.mark.parametrize(
    "feature, cls, responses, readable, count, count_0",
    [
        [hidpp20_constants.FEATURE.COLOR_LED_EFFECTS, hidpp20.LEDEffectsInfo, hidpp.effects_responses_1, 1, 1, 2],
        [hidpp20_constants.FEATURE.RGB_EFFECTS, hidpp20.RGBEffectsInfo, hidpp.effects_responses_2, 1, 1, 2],
    ],
)
def test_LED_RGB_EffectsInfo(feature, cls, responses, readable, count, count_0):
    device = hidpp.Device(feature=feature, responses=responses, offset=0x07)

    effects = cls(device)

    assert effects.readable == readable
    assert effects.count == count
    assert effects.zones[0].count == count_0


@pytest.mark.parametrize(
    "hex, behavior, sector, address, typ, val, modifiers, data, byt",
    [
        ("05010203", 0x0, 0x501, 0x0203, None, None, None, None, None),
        ("15020304", 0x1, 0x502, 0x0304, None, None, None, None, None),
        ("8000FFFF", 0x8, None, None, 0x00, None, None, None, None),
        ("80010102", 0x8, None, None, 0x01, 0x0102, None, None, None),
        ("80020454", 0x8, None, None, 0x02, 0x54, 0x04, None, None),
        ("80030454", 0x8, None, None, 0x03, 0x0454, None, None, None),
        ("900AFF01", 0x9, None, None, None, 0x0A, None, 0x01, None),
        ("709090A0", 0x7, None, None, None, None, None, None, b"\x70\x90\x90\xa0"),
    ],
)
def test_button_bytes(hex, behavior, sector, address, typ, val, modifiers, data, byt):
    button = hidpp20.Button.from_bytes(bytes.fromhex(hex))

    assert getattr(button, "behavior", None) == behavior
    assert getattr(button, "sector", None) == sector
    assert getattr(button, "address", None) == address
    assert getattr(button, "type", None) == typ
    assert getattr(button, "value", None) == val
    assert getattr(button, "modifiers", None) == modifiers
    assert getattr(button, "data", None) == data
    assert getattr(button, "bytes", None) == byt
    assert button.to_bytes().hex().upper() == hex
    assert yaml.safe_load(yaml.dump(button)).to_bytes().hex().upper() == hex


hex1 = (
    "01010290018003000700140028FFFFFF"
    "FFFF0000000000000000000000000000"
    "8000FFFF900AFF00800204548000FFFF"
    "900AFF00800204548000FFFF900AFF00"
    "800204548000FFFF900AFF0080020454"
    "8000FFFF900AFF00800204548000FFFF"
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
hex2 = (
    "01010290018003000700140028FFFFFF"
    "FFFF0000000000000000000000000000"
    "8000FFFF900AFF00800204548000FFFF"
    "900AFF00800204548000FFFF900AFF00"
    "800204548000FFFF900AFF0080020454"
    "8000FFFF900AFF00800204548000FFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "0A01020300500407000000FFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFF27C9"
)
hex3 = (
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    "FFFFFFFFFFFFFFFFFFFFFFFFFF2307"
)


@pytest.mark.parametrize(
    "hex, name, sector, enabled, buttons, gbuttons, resolutions, button, lighting",
    [
        (hex1, "TE7", 2, 1, 16, 0, [0x0190, 0x0380, 0x0700, 0x1400, 0x2800], "8000FFFF", "0A01020300500407000000"),
        (hex2, "", 2, 1, 16, 0, [0x0190, 0x0380, 0x0700, 0x1400, 0x2800], "8000FFFF", "0A01020300500407000000"),
        (hex3, "", 2, 1, 16, 0, [0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF], "FFFFFFFF", "FFFFFFFFFFFFFFFFFFFFFF"),
    ],
)
def test_OnboardProfile_bytes(hex, name, sector, enabled, buttons, gbuttons, resolutions, button, lighting):
    profile = hidpp20.OnboardProfile.from_bytes(sector, enabled, buttons, gbuttons, bytes.fromhex(hex))

    assert profile.name == name
    assert profile.sector == sector
    assert profile.resolutions == resolutions
    assert profile.buttons[0].to_bytes().hex().upper() == button
    assert profile.lighting[0].to_bytes().hex().upper() == lighting

    assert profile.to_bytes(len(hex) // 2).hex().upper() == hex
    assert yaml.safe_load(yaml.dump(profile)).to_bytes(len(hex) // 2).hex().upper() == hex


@pytest.mark.parametrize(
    "responses, name, count, buttons, gbuttons, sectors, size",
    [
        (hidpp.responses_profiles, "ONB", 1, 2, 2, 1, 254),
        (hidpp.responses_profiles_rom, "ONB", 1, 2, 2, 1, 254),
        (hidpp.responses_profiles_rom_2, "ONB", 1, 2, 2, 1, 254),
    ],
)
def test_OnboardProfiles_device(responses, name, count, buttons, gbuttons, sectors, size):
    device = hidpp.Device(name, True, 4.5, responses=responses, feature=hidpp20_constants.FEATURE.ONBOARD_PROFILES, offset=0x9)
    device._profiles = None
    profiles = _hidpp20.get_profiles(device)

    assert profiles
    assert profiles.version == hidpp20.OnboardProfilesVersion
    assert profiles.name == name
    assert profiles.count == count
    assert profiles.buttons == buttons
    assert profiles.gbuttons == gbuttons
    assert profiles.sectors == sectors
    assert profiles.size == size
    assert len(profiles.profiles) == count

    assert yaml.safe_load(yaml.dump(profiles)).to_bytes().hex() == profiles.to_bytes().hex()
