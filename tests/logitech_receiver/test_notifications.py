from logitech_receiver import notifications, hidpp10_constants
from logitech_receiver.base import HIDPPNotification
from logitech_receiver.hidpp10_constants import Registers
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

    def close(self, handle):
        pass


def test__process_receiver_notification_discovery_status_notification_bolt_pairing_error():
    receiver: Receiver = Receiver(MockLowLevelInterface(), None, {}, True, None, None)
    notification = HIDPPNotification(0, 0, Registers.DISCOVERY_STATUS_NOTIFICATION, 0, b'\x01')

    result = notifications._process_receiver_notification(receiver, notification)

    assert result
    assert receiver.pairing.error == hidpp10_constants.BOLT_PAIRING_ERRORS['device_timeout']
    assert receiver.pairing.new_device is None


def test__process_receiver_notification_pairing_status_notification_bolt_pairing_error():
    receiver: Receiver = Receiver(MockLowLevelInterface(), None, {}, True, None, None)
    notification = HIDPPNotification(0, 0, Registers.PAIRING_STATUS_NOTIFICATION, 0, b'\x02')

    result = notifications._process_receiver_notification(receiver, notification)

    assert result
    assert receiver.pairing.error == hidpp10_constants.BOLT_PAIRING_ERRORS['failed']
    assert receiver.pairing.new_device is None
