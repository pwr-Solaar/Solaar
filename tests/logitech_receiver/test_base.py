import pytest

from logitech_receiver import base


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
