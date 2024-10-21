import struct

from unittest import mock

import pytest

from logitech_receiver import base
from logitech_receiver import exceptions
from logitech_receiver.base import HIDPP_SHORT_MESSAGE_ID
from logitech_receiver.base import request
from logitech_receiver.hidpp10_constants import ERROR


@pytest.mark.parametrize(
    "usb_id, expected_name, expected_receiver_kind",
    [
        (0xC548, "Bolt Receiver", "bolt"),
        (0xC52B, "Unifying Receiver", "unifying"),
        (0xC531, "Nano Receiver", "nano"),
        (0xC53F, "Lightspeed Receiver", None),
        (0xC517, "EX100 Receiver 27 Mhz", "27Mhz"),
    ],
)
def test_product_information(usb_id, expected_name, expected_receiver_kind):
    res = base.product_information(usb_id)

    assert res["name"] == expected_name
    assert isinstance(res["vendor_id"], int)
    assert isinstance(res["product_id"], int)

    if expected_receiver_kind:
        assert res["receiver_kind"] == expected_receiver_kind


def test_filter_receivers_known():
    bus_id = 2
    vendor_id = 0x046D
    product_id = 0xC548

    receiver_info = base._filter_receivers(bus_id, vendor_id, product_id)

    assert receiver_info["name"] == "Bolt Receiver"
    assert receiver_info["receiver_kind"] == "bolt"


def test_filter_receivers_unknown():
    bus_id = 1
    vendor_id = 0x046D
    product_id = 0xC500

    receiver_info = base._filter_receivers(bus_id, vendor_id, product_id)

    assert receiver_info["bus_id"] == bus_id
    assert receiver_info["product_id"] == product_id


@pytest.mark.parametrize(
    "product_id, hidpp_short, hidpp_long",
    [
        (0xC548, True, False),
        (0xC07E, True, False),
        (0xC07E, False, True),
        (0xA07E, False, True),
        (0xA07E, None, None),
        (0xA07C, False, False),
    ],
)
def test_filter_products_of_interest(product_id, hidpp_short, hidpp_long):
    bus_id = 3
    vendor_id = 0x046D

    receiver_info = base._filter_products_of_interest(
        bus_id,
        vendor_id,
        product_id,
        hidpp_short=hidpp_short,
        hidpp_long=hidpp_long,
    )

    if not hidpp_short and not hidpp_long:
        assert receiver_info is None
    else:
        assert isinstance(receiver_info["vendor_id"], int)
        assert receiver_info["product_id"] == product_id


@pytest.mark.parametrize(
    "report_id, sub_id, address, valid_notification",
    [
        (0x1, 0x72, 0x57, True),
        (0x1, 0x40, 0x63, True),
        (0x1, 0x40, 0x71, True),
        (0x1, 0x80, 0x71, False),
        (0x1, 0x00, 0x70, False),
        (0x20, 0x09, 0x71, False),
        (0x1, 0x37, 0x71, False),
    ],
)
def test_make_notification(report_id, sub_id, address, valid_notification):
    devnumber = 123
    data = bytes([sub_id, address, 0x02, 0x03, 0x04])

    result = base.make_notification(report_id, devnumber, data)

    if valid_notification:
        assert isinstance(result, base.HIDPPNotification)
        assert result.report_id == report_id
        assert result.devnumber == devnumber
        assert result.sub_id == sub_id
        assert result.address == address
        assert result.data == bytes([0x02, 0x03, 0x04])
    else:
        assert result is None


def test_get_next_sw_id():
    res1 = base._get_next_sw_id()
    res2 = base._get_next_sw_id()

    assert res1 == 2
    assert res2 == 3


@pytest.mark.parametrize(
    "prefix, error_code, return_error, raise_exception",
    [
        (b"\x8f", ERROR.invalid_SubID__command, False, False),
        (b"\x8f", ERROR.invalid_SubID__command, True, False),
        (b"\xff", ERROR.invalid_SubID__command, False, True),
    ],
)
def test_request_errors(prefix: bytes, error_code: ERROR, return_error: bool, raise_exception: bool):
    handle = 0
    device_number = 66

    next_sw_id = 0x02
    reply_data_sw_id = struct.pack("!H", 0x0000 | next_sw_id)

    with (
        mock.patch(
            "logitech_receiver.base._read",
            return_value=(HIDPP_SHORT_MESSAGE_ID, device_number, prefix + reply_data_sw_id + struct.pack("B", error_code)),
        ),
        mock.patch("logitech_receiver.base._skip_incoming", return_value=None),
        mock.patch("logitech_receiver.base.write", return_value=None),
        mock.patch("logitech_receiver.base._get_next_sw_id", return_value=next_sw_id),
    ):
        if raise_exception:
            with pytest.raises(exceptions.FeatureCallError) as context:
                request(handle, device_number, next_sw_id, return_error=return_error)
            assert context.value.number == device_number
            assert context.value.request == next_sw_id
            assert context.value.error == error_code
            assert context.value.params == b""

        else:
            result = request(handle, device_number, next_sw_id, return_error=return_error)
            assert result == (error_code if return_error else None)


@pytest.mark.parametrize(
    "simulated_error, expected_result",
    [
        (ERROR.invalid_SubID__command, 1.0),
        (ERROR.resource_error, None),
        (ERROR.connection_request_failed, None),
        (ERROR.unknown_device, exceptions.NoSuchDevice),
    ],
)
def test_ping_errors(simulated_error: ERROR, expected_result):
    handle = 1
    device_number = 1

    next_sw_id = 0x05
    reply_data_sw_id = struct.pack("!H", 0x0010 | next_sw_id)

    with (
        mock.patch(
            "logitech_receiver.base._read",
            return_value=(HIDPP_SHORT_MESSAGE_ID, device_number, b"\x8f" + reply_data_sw_id + bytes([simulated_error])),
        ),
        mock.patch("logitech_receiver.base._get_next_sw_id", return_value=next_sw_id),
    ):
        if isinstance(expected_result, type) and issubclass(expected_result, Exception):
            with pytest.raises(expected_result) as context:
                base.ping(handle=handle, devnumber=device_number)
            assert context.value.number == device_number
            assert context.value.request == struct.unpack("!H", reply_data_sw_id)[0]

        else:
            result = base.ping(handle=handle, devnumber=device_number)
            assert result == expected_result
