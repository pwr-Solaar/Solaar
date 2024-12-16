import pytest

from logitech_receiver import notifications
from logitech_receiver.base import HIDPPNotification
from logitech_receiver.common import Notification
from logitech_receiver.hidpp10_constants import BoltPairingError
from logitech_receiver.hidpp10_constants import PairingError
from logitech_receiver.hidpp10_constants import Registers
from logitech_receiver.receiver import Receiver


class MockLowLevelInterface:
    def open_path(self, path):
        pass

    def find_paired_node_wpid(self, receiver_path: str, index: int):
        pass

    def ping(self, handle, number, long_message=False):
        pass

    def request(self, handle, devnumber, request_id, *params, **kwargs):
        pass

    def close(self):
        pass


@pytest.mark.parametrize(
    "sub_id, notification_data, expected_error, expected_new_device",
    [
        (Registers.DISCOVERY_STATUS_NOTIFICATION, b"\x01", BoltPairingError.DEVICE_TIMEOUT, None),
        (Registers.PAIRING_STATUS_NOTIFICATION, b"\x02", BoltPairingError.FAILED, None),
        (Notification.PAIRING_LOCK, b"\x01", PairingError.DEVICE_TIMEOUT, None),
        (Notification.PAIRING_LOCK, b"\x02", PairingError.DEVICE_NOT_SUPPORTED, None),
        (Notification.PAIRING_LOCK, b"\x03", PairingError.TOO_MANY_DEVICES, None),
        (Notification.PAIRING_LOCK, b"\x06", PairingError.SEQUENCE_TIMEOUT, None),
    ],
)
def test_process_receiver_notification(sub_id, notification_data, expected_error, expected_new_device):
    receiver: Receiver = Receiver(MockLowLevelInterface(), None, {}, True, None, None)
    notification = HIDPPNotification(0, 0, sub_id, 0, notification_data)

    result = notifications._process_receiver_notification(receiver, notification)

    assert result
    assert receiver.pairing.error == expected_error
    assert receiver.pairing.new_device is expected_new_device
