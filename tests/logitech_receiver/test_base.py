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
