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
from logitech_receiver.hidpp20 import KeyFlag
from logitech_receiver.hidpp20 import MappingFlag
from logitech_receiver.hidpp20_constants import GestureId

from . import fake_hidpp

_hidpp20 = hidpp20.Hidpp20()

device_offline = fake_hidpp.Device("REGISTERS", False)
device_registers = fake_hidpp.Device("OFFLINE", True, 1.0)
device_nofeatures = fake_hidpp.Device("NOFEATURES", True, 4.5)
device_zerofeatures = fake_hidpp.Device("ZEROFEATURES", True, 4.5, [fake_hidpp.Response("0000", 0x0000, "0001")])
device_broken = fake_hidpp.Device(
    "BROKEN", True, 4.5, [fake_hidpp.Response("0500", 0x0000, "0001"), fake_hidpp.Response(None, 0x0100)]
)
device_standard = fake_hidpp.Device("STANDARD", True, 4.5, fake_hidpp.r_keyboard_2)


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
    assert (hidpp20_constants.SupportedFeature.ROOT in featuresarray) == expected_result
    assert len(featuresarray) == expected_count
    assert bool(featuresarray) == expected_result


@pytest.mark.parametrize(
    "device, expected0, expected1, expected2, expected5, expected5v",
    [
        (device_zerofeatures, None, None, None, None, None),
        (device_standard, 0x0000, 0x0001, 0x0020, hidpp20_constants.SupportedFeature.REPROG_CONTROLS_V4, 3),
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
    result5v = featuresarray.get_feature_version(hidpp20_constants.SupportedFeature.REPROG_CONTROLS_V4)

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
                (hidpp20_constants.SupportedFeature.ROOT, 0),
                (hidpp20_constants.SupportedFeature.FEATURE_SET, 1),
                (hidpp20_constants.SupportedFeature.CONFIG_CHANGE, 2),
                (hidpp20_constants.SupportedFeature.DEVICE_FW_VERSION, 3),
                (common.NamedInt(256, "unknown:0100"), 4),
                (hidpp20_constants.SupportedFeature.REPROG_CONTROLS_V4, 5),
                (None, 6),
                (None, 7),
                (hidpp20_constants.SupportedFeature.BATTERY_STATUS, 8),
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

    featuresarray[hidpp20_constants.SupportedFeature.ROOT] = 3
    featuresarray[hidpp20_constants.SupportedFeature.FEATURE_SET] = 5
    featuresarray[hidpp20_constants.SupportedFeature.FEATURE_SET] = 4

    assert featuresarray[hidpp20_constants.SupportedFeature.FEATURE_SET] == 4
    assert featuresarray.inverse[4] == hidpp20_constants.SupportedFeature.FEATURE_SET


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

    result_get0 = featuresarray[hidpp20_constants.SupportedFeature.ROOT]
    result_get1 = featuresarray[hidpp20_constants.SupportedFeature.REPROG_CONTROLS_V4]
    result_get2 = featuresarray[hidpp20_constants.SupportedFeature.GKEY]
    result_1v = featuresarray.get_feature_version(hidpp20_constants.SupportedFeature.REPROG_CONTROLS_V4)

    assert result_get0 == expected0
    assert result_get1 == expected1
    assert result_get2 == expected2
    assert result_1v == expected1v


@pytest.mark.parametrize(
    "device, index, cid, task_id, flags, default_task, expected_flags",
    [
        (device_standard, 2, 1, 1, 0x30, "Volume Up", KeyFlag.REPROGRAMMABLE | KeyFlag.DIVERTABLE),
        (device_standard, 1, 2, 2, 0x20, "Volume Down", KeyFlag.DIVERTABLE),
    ],
)
def test_reprogrammable_key_key(device, index, cid, task_id, flags, default_task, expected_flags):
    key = hidpp20.ReprogrammableKey(device, index, cid, task_id, flags)

    assert key._device == device
    assert key.index == index
    assert key._cid == cid
    assert key._tid == task_id
    assert key._flags == flags
    assert key.key == special_keys.CONTROL[cid]
    assert key.default_task == common.NamedInt(cid, default_task)
    assert key.flags == expected_flags


@pytest.mark.parametrize(
    "device, index, cid, task_id, flags, pos, group, gmask, default_task, expected_flags, group_names",
    [
        (
            device_standard,
            1,
            0x51,
            0x39,
            0x60,
            0,
            1,
            1,
            "Right Click",
            KeyFlag.DIVERTABLE | KeyFlag.PERSISTENTLY_DIVERTABLE,
            ["g1"],
        ),
        (
            device_standard,
            2,
            0x52,
            0x3A,
            0x11,
            1,
            2,
            3,
            "Mouse Middle Button",
            KeyFlag.MSE | KeyFlag.REPROGRAMMABLE,
            ["g1", "g2"],
        ),
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
            KeyFlag.REPROGRAMMABLE | KeyFlag.RAW_XY,
            ["g1", "g2", "g3"],
        ),
    ],
)
def test_reprogrammable_key_v4_key(
    device, index, cid, task_id, flags, pos, group, gmask, default_task, expected_flags, group_names
):
    key = hidpp20.ReprogrammableKeyV4(device, index, cid, task_id, flags, pos, group, gmask)

    assert key._device == device
    assert key.index == index
    assert key._cid == cid
    assert key._tid == task_id
    assert key._flags == flags
    assert key.pos == pos
    assert key.group == group
    assert key._gmask == gmask
    assert key.key == special_keys.CONTROL[cid]
    assert key.default_task == common.NamedInt(cid, default_task)
    assert key.flags == expected_flags
    assert list(key.group_mask) == group_names


@pytest.mark.parametrize(
    "responses, index, mapped_to, remappable_to, expected_mapping_flags",
    [
        (fake_hidpp.responses_key, 1, "Right Click", common.UnsortedNamedInts(Right_Click=81, Left_Click=80), MappingFlag(0)),
        (fake_hidpp.responses_key, 2, "Left Click", None, MappingFlag.DIVERTED),
        (fake_hidpp.responses_key, 3, "Mouse Back Button", None, MappingFlag.DIVERTED | MappingFlag.PERSISTENTLY_DIVERTED),
        (fake_hidpp.responses_key, 4, "Mouse Forward Button", None, MappingFlag.DIVERTED | MappingFlag.RAW_XY_DIVERTED),
    ],
)
# these fields need access all the key data, so start by setting up a device and its key data
def test_reprogrammable_key_v4_query(responses, index, mapped_to, remappable_to, expected_mapping_flags):
    device = fake_hidpp.Device(
        "KEY", responses=responses, feature=hidpp20_constants.SupportedFeature.REPROG_CONTROLS_V4, offset=5
    )
    device._keys = _hidpp20.get_keys(device)

    key = device.keys[index]

    assert key.mapped_to == mapped_to
    assert (key.remappable_to == remappable_to) or remappable_to is None
    assert key.mapping_flags == expected_mapping_flags


@pytest.mark.parametrize(
    "responses, index, diverted, persistently_diverted, rawXY_reporting, remap, sets",
    [
        (fake_hidpp.responses_key, 1, True, False, True, 0x52, ["0051080000"]),
        (fake_hidpp.responses_key, 2, False, True, False, 0x51, ["0052020000", "0052200000", "0052000051"]),
        (fake_hidpp.responses_key, 3, False, True, True, 0x50, ["0053020000", "00530C0000", "0053300000", "0053000050"]),
        (fake_hidpp.responses_key, 4, False, False, False, 0x50, ["0056020000", "0056080000", "0056200000", "0056000050"]),
    ],
)
def test_reprogrammable_key_v4_set(responses, index, diverted, persistently_diverted, rawXY_reporting, remap, sets, mocker):
    responses += [fake_hidpp.Response(r, 0x530, r) for r in sets]
    device = fake_hidpp.Device(
        "KEY", responses=responses, feature=hidpp20_constants.SupportedFeature.REPROG_CONTROLS_V4, offset=5
    )
    device._keys = _hidpp20.get_keys(device)
    device._keys._ensure_all_keys_queried()  # do this now so that the last requests are sets
    spy_request = mocker.spy(device, "request")

    key = device.keys[index]
    _mapping_flags = key.mapping_flags

    if hidpp20.KeyFlag.DIVERTABLE in key.flags or not diverted:
        key.set_diverted(diverted)
    else:
        with pytest.raises(exceptions.FeatureNotSupported):
            key.set_diverted(diverted)
    assert (MappingFlag.DIVERTED in key.mapping_flags) == (diverted and hidpp20.KeyFlag.DIVERTABLE in key.flags)

    if hidpp20.KeyFlag.PERSISTENTLY_DIVERTABLE in key.flags or not persistently_diverted:
        key.set_persistently_diverted(persistently_diverted)
    else:
        with pytest.raises(exceptions.FeatureNotSupported):
            key.set_persistently_diverted(persistently_diverted)
    assert (hidpp20.MappingFlag.PERSISTENTLY_DIVERTED in key.mapping_flags) == (
        persistently_diverted and hidpp20.KeyFlag.PERSISTENTLY_DIVERTABLE in key.flags
    )

    if hidpp20.KeyFlag.RAW_XY in key.flags or not rawXY_reporting:
        key.set_rawXY_reporting(rawXY_reporting)
    else:
        with pytest.raises(exceptions.FeatureNotSupported):
            key.set_rawXY_reporting(rawXY_reporting)
    assert (MappingFlag.RAW_XY_DIVERTED in key.mapping_flags) == (rawXY_reporting and hidpp20.KeyFlag.RAW_XY in key.flags)

    if remap in key.remappable_to or remap == 0:
        key.remap(remap)
    else:
        with pytest.raises(exceptions.FeatureNotSupported):
            key.remap(remap)
    assert (key.mapped_to == remap) or (remap not in key.remappable_to and remap != 0)

    fake_hidpp.match_requests(len(sets), responses, spy_request.call_args_list)


@pytest.mark.parametrize(
    "r, index, cid, actionId, remapped, mask, status, action, modifiers, byts, remap",
    [
        (fake_hidpp.responses_key, 1, 0x0051, 0x02, 0x0002, 0x01, 0, "Mouse Button: 2", "Cntrl+", "02000201", "01000400"),
        (fake_hidpp.responses_key, 2, 0x0052, 0x01, 0x0001, 0x00, 1, "Key: 1", "", "01000100", "02005004"),
        (fake_hidpp.responses_key, 3, 0x0053, 0x02, 0x0001, 0x00, 1, "Mouse Button: 1", "", "02000100", "7FFFFFFF"),
    ],
)
def test_remappable_action(r, index, cid, actionId, remapped, mask, status, action, modifiers, byts, remap, mocker):
    if int(remap, 16) == special_keys.KEYS_Default:
        responses = r + [
            fake_hidpp.Response("040000", 0x0000, "1C00"),
            fake_hidpp.Response("00", 0x450, f"{cid:04X}" + "FF"),
        ]
    else:
        responses = r + [
            fake_hidpp.Response("040000", 0x0000, "1C00"),
            fake_hidpp.Response("00", 0x440, f"{cid:04X}" + "FF" + remap),
        ]
    device = fake_hidpp.Device(
        "KEY", responses=responses, feature=hidpp20_constants.SupportedFeature.REPROG_CONTROLS_V4, offset=5
    )
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
        fake_hidpp.match_requests(1, responses, spy_request.call_args_list)


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
    "device, count, index, cid, task_id, flags, pos, group, gmask",
    [
        (device_standard, 4, 0, 0x0011, 0x0012, 0xCDAB, 1, 2, 3),
        (device_standard, 6, 1, 0x0111, 0x0022, 0xCDAB, 1, 2, 3),
        (device_standard, 8, 3, 0x0311, 0x0032, 0xCDAB, 1, 2, 4),
    ],
)
def test_KeysArrayV4__getitem(device, count, index, cid, task_id, flags, pos, group, gmask):
    keysarray = hidpp20.KeysArrayV4(device, count)

    result = keysarray[index]

    assert result._device == device
    assert result.index == index
    assert result._cid == cid
    assert result._tid == task_id
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


device_key = fake_hidpp.Device(
    "KEY", responses=fake_hidpp.responses_key, feature=hidpp20_constants.SupportedFeature.REPROG_CONTROLS_V4, offset=5
)


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
def test_keys_array_v4_key(key, expected_index, expected_mapped_to, expected_remappable_to):
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
        (fake_hidpp.responses_remap, special_keys.CONTROL.Left_Button, 0, common.NamedInt(0x01, "Mouse Button Left"), 0x41),
        (fake_hidpp.responses_remap, special_keys.CONTROL.Right_Button, 1, common.NamedInt(0x01, "Mouse Button Left"), 0x41),
        (fake_hidpp.responses_remap, special_keys.CONTROL.Middle_Button, 2, common.NamedInt(0x51, "DOWN"), 0x41),
    ],
)
def test_KeysArrayPersistent_key(responses, key, index, mapped_to, capabilities):
    device = fake_hidpp.Device(
        "REMAP", responses=responses, feature=hidpp20_constants.SupportedFeature.PERSISTENT_REMAPPABLE_ACTION
    )
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
        (device_standard, 0x01, 0x01, 5, 10, GestureId.TAP_1_FINGER, True, 5, None, (0, 0x20), (None, None)),
        (device_standard, 0x03, 0x02, 6, 11, GestureId.TAP_3_FINGER, False, None, 11, (None, None), (1, 0x08)),
    ],
)
def test_gesture(device, low, high, next_index, next_diversion_index, name, cbe, si, sdi, eom, dom):
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
        (fake_hidpp.responses_gestures, 20, None, None, None, None, None, None),
        (fake_hidpp.responses_gestures, 1, True, False, "01", "00", "01", "00"),
        (fake_hidpp.responses_gestures, 45, False, None, "01", "00", None, None),
    ],
)
def test_Gesture_set(responses, gest, enabled, diverted, set_result, unset_result, divert_result, undivert_result):
    device = fake_hidpp.Device("GESTURE", responses=responses, feature=hidpp20_constants.SupportedFeature.GESTURE_2)
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
        (fake_hidpp.responses_gestures, 4, hidpp20_constants.ParamId.SCALE_FACTOR, 0, 2, 256, 256, "0080", "0180"),
    ],
)
def test_param(responses, prm, id, index, size, value, default_value, write1, write2):
    device = fake_hidpp.Device("GESTURE", responses=responses, feature=hidpp20_constants.SupportedFeature.GESTURE_2)
    gestures = _hidpp20.get_gestures(device)

    param = gestures.param(prm)

    assert param.id == id
    assert param.index == index
    assert param.size == size
    assert param.value == value
    assert param.default_value == default_value
    assert param.param == id
    assert int(param) == id
    assert param.write(bytes.fromhex(write1)).hex().upper() == f"{index:02X}" + write1 + "FF"
    assert param.write(bytes.fromhex(write2)).hex().upper() == f"{index:02X}" + write2 + "FF"


@pytest.mark.parametrize(
    "responses, id, s, byte_count, expected_value, expected_string",
    [
        (fake_hidpp.responses_gestures, 1, hidpp20.SpecGesture.DVI_FIELD_WIDTH, 1, 8, "[dvi field width=8]"),
        (fake_hidpp.responses_gestures, 2, hidpp20.SpecGesture.FIELD_WIDTHS, 1, 8, "[field widths=8]"),
        (fake_hidpp.responses_gestures, 3, hidpp20.SpecGesture.PERIOD_UNIT, 2, 2048, "[period unit=2048]"),
    ],
)
def test_spec(responses, id, s, byte_count, expected_value, expected_string):
    device = fake_hidpp.Device("GESTURE", responses=responses, feature=hidpp20_constants.SupportedFeature.GESTURE_2)
    gestures = _hidpp20.get_gestures(device)

    spec = gestures.specs[id]

    assert spec.id == id
    assert spec.spec == s
    assert spec.byte_count == byte_count
    assert spec.value == expected_value
    assert repr(spec) == expected_string


def test_Gestures():
    device = fake_hidpp.Device(
        "GESTURES", responses=fake_hidpp.responses_gestures, feature=hidpp20_constants.SupportedFeature.GESTURE_2
    )
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
    fake_hidpp.Response("010118000001020003000400", 0x0400),
    fake_hidpp.Response("0101FF00020003000400", 0x0410, "0101FF00020003000400"),
]

device_backlight = fake_hidpp.Device(
    "BACKLIGHT", responses=responses_backlight, feature=hidpp20_constants.SupportedFeature.BACKLIGHT2
)


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
        [
            hidpp20_constants.SupportedFeature.COLOR_LED_EFFECTS,
            0x20,
            fake_hidpp.Response("0102000300040005", 0x0420, "010200"),
            3,
            4,
            5,
        ],
        [
            hidpp20_constants.SupportedFeature.COLOR_LED_EFFECTS,
            0x20,
            fake_hidpp.Response("0102000700080009", 0x0420, "010200"),
            7,
            8,
            9,
        ],
    ],
)
def test_LEDEffectInfo(feature, function, response, ID, capabilities, period):
    device = fake_hidpp.Device(feature=feature, responses=[response])

    info = hidpp20.LEDEffectInfo(feature, function, device, 1, 2)

    assert info.zindex == 1
    assert info.index == 2
    assert info.ID == ID
    assert info.capabilities == capabilities
    assert info.period == period


@pytest.mark.parametrize(
    "feature, function, offset, effect_function, responses, index, location, count, id_1",
    [
        [hidpp20_constants.SupportedFeature.COLOR_LED_EFFECTS, 0x10, 0, 0x20, fake_hidpp.zone_responses_1, 0, 1, 2, 0xB],
        [hidpp20_constants.SupportedFeature.RGB_EFFECTS, 0x00, 1, 0x00, fake_hidpp.zone_responses_2, 0, 1, 2, 2],
    ],
)
def test_LEDZoneInfo(feature, function, offset, effect_function, responses, index, location, count, id_1):
    device = fake_hidpp.Device(feature=feature, responses=responses, offset=0x07)

    zone = hidpp20.LEDZoneInfo(feature, function, offset, effect_function, device, index)

    assert zone.index == index
    assert zone.location == location
    assert zone.count == count
    assert len(zone.effects) == count
    assert zone.effects[1].ID == id_1


@pytest.mark.parametrize(
    "responses, setting, expected_command",
    [
        [fake_hidpp.zone_responses_1, hidpp20.LEDEffectSetting(ID=0), None],
        [fake_hidpp.zone_responses_1, hidpp20.LEDEffectSetting(ID=3, period=0x20, intensity=0x50), "000000000000000020500000"],
        [
            fake_hidpp.zone_responses_1,
            hidpp20.LEDEffectSetting(ID=0xB, color=0x808080, period=0x20),
            "000180808000002000000000",
        ],
    ],
)
def test_LEDZoneInfo_to_command(responses, setting, expected_command):
    device = fake_hidpp.Device(feature=hidpp20_constants.SupportedFeature.COLOR_LED_EFFECTS, responses=responses, offset=0x07)
    zone = hidpp20.LEDZoneInfo(hidpp20_constants.SupportedFeature.COLOR_LED_EFFECTS, 0x10, 0, 0x20, device, 0)

    command = zone.to_command(setting)

    assert command == (bytes.fromhex(expected_command) if expected_command is not None else None)


@pytest.mark.parametrize(
    "feature, cls, responses, readable, count, count_0",
    [
        [
            hidpp20_constants.SupportedFeature.COLOR_LED_EFFECTS,
            hidpp20.LEDEffectsInfo,
            fake_hidpp.effects_responses_1,
            1,
            1,
            2,
        ],
        [hidpp20_constants.SupportedFeature.RGB_EFFECTS, hidpp20.RGBEffectsInfo, fake_hidpp.effects_responses_2, 1, 1, 2],
    ],
)
def test_LED_RGB_EffectsInfo(feature, cls, responses, readable, count, count_0):
    device = fake_hidpp.Device(feature=feature, responses=responses, offset=0x07)

    effects = cls(device)

    assert effects.readable == readable
    assert effects.count == count
    assert effects.zones[0].count == count_0


@pytest.mark.parametrize(
    "hex, expected_behavior, sector, address, typ, val, modifiers, data, byt",
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
def test_button_bytes(hex, expected_behavior, sector, address, typ, val, modifiers, data, byt):
    button = hidpp20.Button.from_bytes(bytes.fromhex(hex))

    assert getattr(button, "behavior", None) == expected_behavior
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
def test_onboard_profile_bytes(hex, name, sector, enabled, buttons, gbuttons, resolutions, button, lighting):
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
        (fake_hidpp.responses_profiles, "ONB", 1, 2, 2, 1, 254),
        (fake_hidpp.responses_profiles_rom, "ONB", 1, 2, 2, 1, 254),
        (fake_hidpp.responses_profiles_rom_2, "ONB", 1, 2, 2, 1, 254),
    ],
)
def test_onboard_profiles_device(responses, name, count, buttons, gbuttons, sectors, size):
    device = fake_hidpp.Device(
        name, True, 4.5, responses=responses, feature=hidpp20_constants.SupportedFeature.ONBOARD_PROFILES, offset=0x9
    )
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

    yml_dump = yaml.dump(profiles)
    assert yaml.safe_load(yml_dump).to_bytes().hex() == profiles.to_bytes().hex()
