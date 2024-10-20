from enum import IntFlag

import pytest
import yaml

from logitech_receiver import common


def test_crc16():
    value = b"123456789"
    expected = 0x29B1

    result = common.crc16(value)

    assert result == expected


def test_named_int():
    named_int = common.NamedInt(0x2, "pulse")

    assert named_int.name == "pulse"
    assert named_int == 2
    assert repr(named_int) == "NamedInt(2, 'pulse')"


def test_named_int_comparison():
    named_int = common.NamedInt(0, "entry")
    named_int_equal = common.NamedInt(0, "entry")
    named_int_unequal_name = common.NamedInt(0, "unequal")
    named_int_unequal_value = common.NamedInt(5, "entry")
    named_int_unequal = common.NamedInt(2, "unequal")

    assert named_int == named_int_equal
    assert named_int != named_int_unequal_name
    assert named_int != named_int_unequal_value
    assert named_int != named_int_unequal
    assert named_int is not None
    assert named_int == 0
    assert named_int == "entry"


def test_named_int_comparison_exception():
    named_int = common.NamedInt(0, "entry")

    with pytest.raises(TypeError):
        assert named_int == b"\x00"


def test_named_int_conversions():
    named_int = common.NamedInt(2, "two")

    assert named_int.bytes() == b"\x00\x02"
    assert str(named_int) == "two"


def test_named_int_yaml():
    named_int = common.NamedInt(2, "two")

    yaml_string = yaml.dump(named_int)

    #    assert yaml_string == "!NamedInt {name: two, value: 2}\n"

    yaml_load = yaml.safe_load(yaml_string)

    assert yaml_load == named_int


def test_named_ints():
    named_ints = common.NamedInts(empty=0, critical=5, low=20, good=50, full=90)

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
    assert named_ints["5"] is None
    assert len(named_ints[:]) == len(named_ints)
    assert len(named_ints[0:100]) == len(named_ints)
    assert len(named_ints[5:90]) == 3
    assert len(named_ints[5:]) == 4
    assert named_ints[90:5] == []


def test_named_ints_fallback():
    named_ints = common.NamedInts(empty=0, critical=5, low=20, good=50, full=90)
    named_ints._fallback = lambda x: str(x)

    fallback = named_ints[80]

    assert fallback == common.NamedInt(80, "80")


def test_named_ints_list():
    named_ints_list = common.NamedInts.list([0, 5, 20, 50, 90])

    assert len(named_ints_list) == 5
    assert 50 in named_ints_list
    assert 60 not in named_ints_list


def test_named_ints_range():
    named_ints_range = common.NamedInts.range(0, 5)

    assert len(named_ints_range) == 6
    assert 4 in named_ints_range
    assert 6 not in named_ints_range


@pytest.mark.parametrize(
    "code, expected_flags",
    [
        (0, []),
        (0b0010, ["two"]),
        (0b0101, ["one", "three"]),
        (0b1001, ["one", "unknown:000008"]),
    ],
)
def test_named_ints_flag_names(code, expected_flags):
    named_ints_flag_bits = common.NamedInts(one=0b001, two=0b010, three=0b100)

    flags = list(named_ints_flag_bits.flag_names(code))

    assert flags == expected_flags


@pytest.mark.parametrize(
    "code, expected_flags",
    [
        (0, []),
        (0b0010, ["two"]),
        (0b0101, ["one", "three"]),
        (0b1001, ["one", "unknown:000008"]),
    ],
)
def test_flag_names(code, expected_flags):
    class ExampleFlag(IntFlag):
        one = 0x1
        two = 0x2
        three = 0x4

    flags = common.flag_names(ExampleFlag, code)

    assert list(flags) == expected_flags


def test_named_ints_setitem():
    named_ints = common.NamedInts(empty=0, critical=5, low=20, good=50, full=90)

    named_ints[55] = "better"
    named_ints[60] = common.NamedInt(60, "sixty")
    with pytest.raises(TypeError):
        named_ints[70] = 70
    with pytest.raises(ValueError):
        named_ints[70] = "empty"
    with pytest.raises(ValueError):
        named_ints[50] = "new"

    assert named_ints[55] == "better"
    assert named_ints[60] == "sixty"


def test_named_ints_other():
    named_ints = common.NamedInts(empty=0, critical=5)
    named_ints_2 = common.NamedInts(good=50)

    union = named_ints.__or__(named_ints_2)

    assert list(named_ints) == [common.NamedInt(0, "empty"), common.NamedInt(5, "critical")]
    assert len(named_ints) == 2
    assert repr(named_ints) == "NamedInts(NamedInt(0, 'empty'), NamedInt(5, 'critical'))"
    assert len(union) == 3
    assert list(union) == [common.NamedInt(0, "empty"), common.NamedInt(5, "critical"), common.NamedInt(50, "good")]


def test_unsorted_named_ints():
    named_ints = common.UnsortedNamedInts(critical=5, empty=0)
    named_ints_2 = common.UnsortedNamedInts(good=50)

    union = named_ints.__or__(named_ints_2)
    unionr = named_ints_2.__or__(named_ints)

    assert len(union) == 3
    assert list(union) == [common.NamedInt(5, "critical"), common.NamedInt(0, "empty"), common.NamedInt(50, "good")]
    assert len(unionr) == 3
    assert list(unionr) == [common.NamedInt(50, "good"), common.NamedInt(5, "critical"), common.NamedInt(0, "empty")]


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


def test_kw_exception():
    e = common.KwException(foo=0, bar="bar")

    assert e.foo == 0
    assert e.bar == "bar"


@pytest.mark.parametrize(
    "status, expected_level, expected_ok, expected_charging, expected_string",
    [
        (common.BatteryStatus.FULL, common.BatteryLevelApproximation.FULL, True, True, "Battery: full (full)"),
        (common.BatteryStatus.ALMOST_FULL, common.BatteryLevelApproximation.GOOD, True, True, "Battery: good (almost full)"),
        (common.BatteryStatus.RECHARGING, common.BatteryLevelApproximation.GOOD, True, True, "Battery: good (recharging)"),
        (
            common.BatteryStatus.SLOW_RECHARGE,
            common.BatteryLevelApproximation.LOW,
            True,
            True,
            "Battery: low (slow recharge)",
        ),
        (common.BatteryStatus.DISCHARGING, None, True, False, ""),
    ],
)
def test_battery(status, expected_level, expected_ok, expected_charging, expected_string):
    battery = common.Battery(None, None, status, None)

    assert battery.status == status
    assert battery.level == expected_level
    assert battery.ok() == expected_ok
    assert battery.charging() == expected_charging
    assert battery.to_str() == expected_string


def test_battery_2():
    battery = common.Battery(50, None, common.BatteryStatus.DISCHARGING, None)

    assert battery.status == common.BatteryStatus.DISCHARGING
    assert battery.level == 50
    assert battery.ok()
    assert not battery.charging()
    assert battery.to_str() == "Battery: 50% (discharging)"
