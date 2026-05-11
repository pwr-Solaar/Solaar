import pytest

from logitech_receiver import base_usb
from logitech_receiver.common import LOGITECH_VENDOR_ID


def test_ensure_known_receivers_mappings_are_valid():
    for key, receiver in base_usb.KNOWN_RECEIVERS.items():
        assert key == receiver["product_id"]


def test_get_receiver_info():
    expected = {
        "vendor_id": LOGITECH_VENDOR_ID,
        "product_id": 0xC548,
        "usb_interface": 2,
        "name": "Bolt Receiver",
        "receiver_kind": "bolt",
        "max_devices": 6,
        "may_unpair": True,
    }

    res = base_usb.get_receiver_info(0xC548)

    assert res == expected


def test_get_receiver_info_unknown_device_fails():
    with pytest.raises(ValueError):
        base_usb.get_receiver_info(0xC500)
