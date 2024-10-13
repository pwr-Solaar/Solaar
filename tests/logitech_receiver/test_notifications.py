from unittest import mock

import pytest

from logitech_receiver import hidpp10_constants
from logitech_receiver import notifications
from logitech_receiver.base import HIDPPNotification

from logitech_receiver.hidpp10_constants import Registers
from logitech_receiver.receiver import LowLevelInterface
from logitech_receiver.receiver import Receiver


# Create a mock LowLevelInterface for testing
class MockLowLevelInterface:
    def open_path(self, path):
        pass

    def find_paired_node_wpid(self, receiver_path: str, index: int):
        pass

    def ping(self, handle, number, long_message=False):
        pass

    def request(self, handle, devnumber, request_id, *params, **kwargs):
        pass


@pytest.mark.parametrize(
    "sub_id, notification_data, expected_error, expected_new_device",
    [
        (Registers.DISCOVERY_STATUS_NOTIFICATION, b'\x01', "device_timeout", None),
        (Registers.PAIRING_STATUS_NOTIFICATION, b'\x02', "failed", None),
    ]
)
def test_process_receiver_notification_bolt_pairing_error(sub_id, notification_data, expected_error, expected_new_device):
    low_level_mock = mock.Mock(spec=LowLevelInterface)
    serial_reply = b"\x00\x00\x00\x00\x00\x00\x00\x00"
    low_level_mock.read_register = mock.Mock(return_value=serial_reply)

    receiver: Receiver = Receiver(MockLowLevelInterface(), None, {}, True, None, None)
    notification = HIDPPNotification(0, 0, sub_id, 0, notification_data)

    result = notifications._process_receiver_notification(receiver, notification)

    assert result
    assert receiver.pairing.error == hidpp10_constants.BOLT_PAIRING_ERRORS[expected_error]
    assert receiver.pairing.new_device is expected_new_device
