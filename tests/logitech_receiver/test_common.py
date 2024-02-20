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
