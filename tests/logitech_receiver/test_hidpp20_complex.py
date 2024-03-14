from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Optional

import pytest

from lib.logitech_receiver import common
from lib.logitech_receiver import hidpp20
from lib.logitech_receiver import hidpp20_constants
from lib.logitech_receiver import special_keys


@dataclass
class Response:
    response: Optional[str]
    request_id: int
    params: Any
    no_reply: bool = False


@dataclass
class Device:
    name: str = "DEVICE"
    online: bool = True
    protocol: float = 2.0
    responses: Any = field(default_factory=list)

    def request(self, id, *params, no_reply=False):
        if params is None:
            params = []
        print("REQUEST ", self.name, hex(id), params)
        for r in self.responses:
            if id == r.request_id and params == r.params:
                print("RESPONSE", self.name, hex(r.request_id), r.params, r.response)
                return bytes.fromhex(r.response) if r.response is not None else None

    def feature_request(self, feature, function=0x00, *params, no_reply=False):
        if self.protocol >= 2.0:
            return hidpp20.feature_request(self, feature, function, *params, no_reply=no_reply)


device_offline = Device("REGISTERS", False)
device_registers = Device("OFFLINE", True, 1.0)
device_nofeatures = Device("NOFEATURES", True, 4.5)
device_zerofeatures = Device("ZEROFEATURES", True, 4.5, [Response("0000", 0x0000, (b"\x00\x01",))])
device_broken = Device("BROKEN", True, 4.5, [Response("0500", 0x0000, (b"\x00\x01",)), Response(None, 0x0100, ())])
responses_standard = [
    Response("0100", 0x0000, (b"\x00\x01",)),
    Response("05000300", 0x0000, (b"\x1b\x04",)),
    Response("0500", 0x0100, ()),
    Response("01000000", 0x0110, (0x02,)),
    Response("1B040003", 0x0110, (0x05,)),
    Response("00110012AB010203CD00", 0x0510, (0,)),
    Response("01110022AB010203CD00", 0x0510, (1,)),
    Response("03110032AB010204CD00", 0x0510, (3,)),
    Response("00010111AB010203CD00", 0x0510, (2,)),
    Response("00030333AB010203CD00", 0x0510, (4,)),
]
device_standard = Device("STANDARD", True, 4.5, responses_standard)


@pytest.mark.parametrize(
    "device, expected_result, expected_count",
    [
        (device_offline, False, 0),
        (device_registers, False, 0),
        (device_nofeatures, False, 0),
        (device_zerofeatures, False, 0),
        (device_broken, False, 0),
        (device_standard, True, 6),
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
        (device_standard, 0x0000, 0x0001, 0x0100, hidpp20_constants.FEATURE.REPROG_CONTROLS_V4, 3),
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
                (common.NamedInt(256, "unknown:0100"), 2),
                (None, 3),
                (None, 4),
                (hidpp20_constants.FEATURE.REPROG_CONTROLS_V4, 5),
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


# mapped_to requires ensuring that all keys are set up, so this is done below


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
    Response("0A00", 0x0100, ()),
    Response("01000000", 0x0000, (b"\x00\x01",)),
    Response("09000300", 0x0000, (b"\x1b\x04",)),
    Response("00500038010001010400000000000000", 0x0910, (0,)),
    Response("00510039010001010400000000000000", 0x0910, (1,)),
    Response("0052003A310003070500000000000000", 0x0910, (2,)),
    Response("0053003C310002030500000000000000", 0x0910, (3,)),
    Response("0056003E310002030500000000000000", 0x0910, (4,)),
    Response("00C300A9310003070500000000000000", 0x0910, (5,)),
    Response("00C4009D310003070500000000000000", 0x0910, (6,)),
    Response("00D700B4A00004000300000000000000", 0x0910, (7,)),
    Response("00500000000000000000000000000000", 0x0920, (0, 0x50)),
    Response("00510000000000000000000000000000", 0x0920, (0, 0x51)),
    Response("00520000500000000000000000000000", 0x0920, (0, 0x52)),
    Response("00530000000000000000000000000000", 0x0920, (0, 0x53)),
    Response("00560000000000000000000000000000", 0x0920, (0, 0x56)),
    Response("00C30000000000000000000000000000", 0x0920, (0, 0xC3)),
    Response("00C40000500000000000000000000000", 0x0920, (0, 0xC4)),
    Response("00D70000510000000000000000000000", 0x0920, (0, 0xD7)),
]
device_key = Device("KEY", True, 4.5, responses=responses_key)


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
    device_key.features = hidpp20.FeaturesArray(device_key)
    device_key.features[hidpp20_constants.FEATURE.REPROG_CONTROLS_V4]
    device_key.keys = hidpp20.KeysArrayV4(device_key, 8)
    device_key.keys._ensure_all_keys_queried()

    index = device_key.keys.index(key)
    mapped_to = device_key.keys[expected_index].mapped_to
    remappable_to = device_key.keys[expected_index].remappable_to

    assert index == expected_index
    assert mapped_to == expected_mapped_to
    if expected_remappable_to is not None:
        assert list(remappable_to) == expected_remappable_to
