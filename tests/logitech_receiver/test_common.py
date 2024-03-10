import pytest

from lib.logitech_receiver import common


def test_crc16():
    value = b"123456789"
    expected = 0x29B1

    result = common.crc16(value)

    assert result == expected


def test_named_int():
    named_int = common.NamedInt(0x2, "pulse")

    assert named_int.name == "pulse"
    assert named_int == 2


def test_named_int_comparison():
    default_value = 0
    default_name = "entry"
    named_int = common.NamedInt(default_value, default_name)

    named_int_equal = common.NamedInt(default_value, default_name)
    named_int_unequal_name = common.NamedInt(default_value, "unequal")
    named_int_unequal_value = common.NamedInt(5, default_name)
    named_int_unequal = common.NamedInt(2, "unequal")

    assert named_int == named_int_equal
    assert named_int != named_int_unequal_name
    assert named_int != named_int_unequal_value
    assert named_int != named_int_unequal
    assert named_int is not None
    assert named_int == 0
    assert named_int == "entry"


def test_named_int_conversions():
    named_int = common.NamedInt(2, "two")

    assert named_int.bytes() == b"\x00\x02"
    assert str(named_int) == "two"


@pytest.fixture
def named_ints():
    return common.NamedInts(empty=0, critical=5, low=20, good=50, full=90)


def test_named_ints(named_ints):
    assert named_ints.empty == 0
    assert named_ints.empty.name == "empty"
    assert named_ints.critical == 5
    assert named_ints.critical.name == "critical"
    assert named_ints.low == 20
    assert named_ints.low.name == "low"
    assert named_ints.good == 50
    assert named_ints.good.name == "good"
    assert named_ints.full == 90
    assert named_ints.full.name == "full"

    assert len(named_ints) == 5
    assert 5 in named_ints
    assert 6 not in named_ints
    assert "critical" in named_ints
    assert "easy" not in named_ints
    assert common.NamedInt(5, "critical") in named_ints
    assert common.NamedInt(5, "five") not in named_ints
    assert common.NamedInt(6, "critical") not in named_ints
    assert named_ints[5] == "critical"
    assert named_ints["critical"] == "critical"
    assert named_ints[66] is None


def test_named_ints_list():
    named_ints_list = common.NamedInts.list([0, 5, 20, 50, 90])

    assert len(named_ints_list) == 5
    assert 50 in named_ints_list
    assert 60 not in named_ints_list


def test_named_ints_range(named_ints):
    named_ints_range = common.NamedInts.range(0, 5)

    assert len(named_ints_range) == 6
    assert 4 in named_ints_range
    assert 6 not in named_ints_range


@pytest.mark.parametrize(
    "bytes_input, expected_output",
    [
        (b"\x01\x02\x03\x04", "01020304"),
        (b"", ""),
    ],
)
def test_strhex(bytes_input, expected_output):
    result = common.strhex(bytes_input)

    assert result == expected_output


def test_bytest2int():
    value = b"\x12\x34\x56\x78"
    expected = 0x12345678

    result = common.bytes2int(value)

    assert result == expected


def test_int2bytes():
    value = 0x12345678
    expected = b"\x12\x34\x56\x78"

    result = common.int2bytes(value)

    assert result == expected


def test_battery():
    battery = common.Battery(None, None, common.Battery.STATUS.full, None)

    assert battery.status == common.Battery.STATUS.full
    assert battery.level == common.Battery.APPROX.full
    assert battery.ok()
    assert battery.charging()
    assert battery.to_str() == "Battery: full (full)"


def test_battery_2():
    battery = common.Battery(50, None, common.Battery.STATUS.discharging, None)

    assert battery.status == common.Battery.STATUS.discharging
    assert battery.level == 50
    assert battery.ok()
    assert not battery.charging()
    assert battery.to_str() == "Battery: 50% (discharging)"
