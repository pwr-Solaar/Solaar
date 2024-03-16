from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Optional

import pytest

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

    def request(self, id, params=None, no_reply=False):
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
device_zerofeatures = Device("ZEROFEATURES", True, 4.5, [Response("0000", 0x0000, b"\x00\x01")])
device_broken = Device("BROKEN", True, 4.5, [Response("0000", 0x0000, b"\x00\x01"), Response(None, 0x0100, [])])

responses_standard = [
    Response("0100", 0x0000, b"\x00\x01"),
    Response("05000300", 0x0000, b"\x1b\x04"),
    Response("0500", 0x0100, []),
    Response("01000000", 0x0110, 0x02),
    Response("1B040003", 0x0110, 0x05),
    Response("00110012AB010203CD00", 0x0510, 0),
    Response("01110022AB010203CD00", 0x0510, 1),
    Response("03110032AB010204CD00", 0x0510, 3),
    Response("00010111AB010203CD00", 0x0510, 2),
    Response("00030333AB010203CD00", 0x0510, 4),
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
