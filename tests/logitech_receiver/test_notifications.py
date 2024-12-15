import pytest

from logitech_receiver import notifications
from logitech_receiver.base import HIDPPNotification
from logitech_receiver.common import Notification
from logitech_receiver.hidpp10_constants import BoltPairingError
from logitech_receiver.hidpp10_constants import PairingError
from logitech_receiver.hidpp10_constants import Registers
from logitech_receiver.hidpp20_constants import SupportedFeature
from logitech_receiver.receiver import Receiver

from . import fake_hidpp


class MockLowLevelInterface:
    def open_path(self, path):
        pass

    def find_paired_node_wpid(self, receiver_path: str, index: int):
        pass

    def ping(self, handle, number, long_message=False):
        pass

    def request(self, handle, devnumber, request_id, *params, **kwargs):
        pass

    def find_paired_node(self, receiver_path: str, index: int, timeout: int):
        return None

    def close(self, device_handle) -> None:
        pass


@pytest.mark.parametrize(
    "sub_id, notification_data, expected_error, expected_new_device",
    [
        (Registers.DISCOVERY_STATUS_NOTIFICATION, b"\x01", BoltPairingError.DEVICE_TIMEOUT, None),
        (
            Registers.DEVICE_DISCOVERY_NOTIFICATION,
            b"\x01\x01\x01\x01\x01\x01\x01\x01\x01",
            None,
            None,
        ),
        (Registers.PAIRING_STATUS_NOTIFICATION, b"\x02", BoltPairingError.FAILED, None),
        (Notification.PAIRING_LOCK, b"\x01", PairingError.DEVICE_TIMEOUT, None),
        (Notification.PAIRING_LOCK, b"\x02", PairingError.DEVICE_NOT_SUPPORTED, None),
        (Notification.PAIRING_LOCK, b"\x03", PairingError.TOO_MANY_DEVICES, None),
        (Notification.PAIRING_LOCK, b"\x06", PairingError.SEQUENCE_TIMEOUT, None),
        (Registers.PASSKEY_REQUEST_NOTIFICATION, b"\x06", None, None),
        (Registers.PASSKEY_PRESSED_NOTIFICATION, b"\x06", None, None),
    ],
)
def test_process_receiver_notification(sub_id, notification_data, expected_error, expected_new_device):
    receiver: Receiver = Receiver(MockLowLevelInterface(), None, {}, True, None, None)
    notification = HIDPPNotification(0, 0, sub_id, 0x02, notification_data)

    result = notifications._process_receiver_notification(receiver, notification)

    assert result
    assert receiver.pairing.error == expected_error
    assert receiver.pairing.new_device is expected_new_device


@pytest.mark.parametrize(
    "hidpp_notification, expected",
    [
        (HIDPPNotification(0, 0, sub_id=Registers.BATTERY_STATUS, address=0, data=b"0x01"), False),
        (HIDPPNotification(0, 0, sub_id=Notification.NO_OPERATION, address=0, data=b"0x01"), False),
        (HIDPPNotification(0, 0, sub_id=0x40, address=0, data=b"0x01"), True),
    ],
)
def test_process_device_notification(hidpp_notification, expected):
    device = fake_hidpp.Device()

    result = notifications._process_device_notification(device, hidpp_notification)

    assert result == expected


@pytest.mark.parametrize(
    "hidpp_notification, expected",
    [
        (HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0, data=b"0x01"), True),
        (HIDPPNotification(0, 0, sub_id=Notification.DJ_PAIRING, address=0, data=b"0x01"), True),
        (HIDPPNotification(0, 0, sub_id=Notification.CONNECTED, address=0, data=b"0x01"), True),
        (HIDPPNotification(0, 0, sub_id=Notification.RAW_INPUT, address=0, data=b"0x01"), None),
    ],
)
def test_process_dj_notification(hidpp_notification, expected):
    device = fake_hidpp.Device()

    result = notifications._process_dj_notification(device, hidpp_notification)

    assert result == expected


@pytest.mark.parametrize(
    "hidpp_notification, expected",
    [
        (HIDPPNotification(0, 0, sub_id=Registers.BATTERY_STATUS, address=0, data=b"\x01\x00"), True),
        (HIDPPNotification(0, 0, sub_id=Registers.BATTERY_CHARGE, address=0, data=b"0x01\x00"), True),
        (HIDPPNotification(0, 0, sub_id=Notification.RAW_INPUT, address=0, data=b"0x01"), None),
    ],
)
def test_process_hidpp10_custom_notification(hidpp_notification, expected):
    device = fake_hidpp.Device()

    result = notifications._process_hidpp10_custom_notification(device, hidpp_notification)

    assert result == expected


@pytest.mark.parametrize(
    "hidpp_notification, expected",
    [
        (HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x02, data=b"0x01"), True),
        (HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x00, data=b"0x01"), True),
        (HIDPPNotification(0, 0, sub_id=Notification.DJ_PAIRING, address=0x00, data=b"0x01"), True),
        (HIDPPNotification(0, 0, sub_id=Notification.DJ_PAIRING, address=0x02, data=b"0x01"), True),
        (HIDPPNotification(0, 0, sub_id=Notification.DJ_PAIRING, address=0x03, data=b"0x01"), True),
        (HIDPPNotification(0, 0, sub_id=Notification.DJ_PAIRING, address=0x03, data=b"0x4040"), True),
        (HIDPPNotification(0, 0, sub_id=Notification.RAW_INPUT, address=0x00, data=b"0x01"), True),
        (HIDPPNotification(0, 0, sub_id=Notification.POWER, address=0x00, data=b"0x01"), True),
        (HIDPPNotification(0, 0, sub_id=Notification.POWER, address=0x01, data=b"0x01"), True),
        (HIDPPNotification(0, 0, sub_id=Notification.PAIRING_LOCK, address=0x01, data=b"0x01"), None),
    ],
)
def test_process_hidpp10_notification(hidpp_notification, expected):
    fake_device = fake_hidpp.Device()
    fake_device.receiver = ["rec1", "rec2"]

    result = notifications._process_hidpp10_notification(fake_device, hidpp_notification)

    assert result == expected


@pytest.mark.parametrize(
    "hidpp_notification, feature",
    [
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x00, data=b"0x01"),
            SupportedFeature.BATTERY_STATUS,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x02, data=b"0x01"),
            SupportedFeature.BATTERY_STATUS,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x00, data=b"0x01"),
            SupportedFeature.BATTERY_VOLTAGE,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x05, data=b"0x01"),
            SupportedFeature.BATTERY_VOLTAGE,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x00, data=b"0x01"),
            SupportedFeature.UNIFIED_BATTERY,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x02, data=b"0x01"),
            SupportedFeature.UNIFIED_BATTERY,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x00, data=b"0x01"),
            SupportedFeature.ADC_MEASUREMENT,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x02, data=b"0x01"),
            SupportedFeature.ADC_MEASUREMENT,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x00, data=b"01234GOOD"),
            SupportedFeature.SOLAR_DASHBOARD,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x10, data=b"01234GOOD"),
            SupportedFeature.SOLAR_DASHBOARD,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x20, data=b"01234GOOD"),
            SupportedFeature.SOLAR_DASHBOARD,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x02, data=b"01234GOOD"),
            SupportedFeature.SOLAR_DASHBOARD,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x02, data=b"CHARGENOTGOOD"),
            SupportedFeature.SOLAR_DASHBOARD,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x00, data=b"\x01\x01\x02"),
            SupportedFeature.WIRELESS_DEVICE_STATUS,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x02, data=b"0x01"),
            SupportedFeature.WIRELESS_DEVICE_STATUS,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x00, data=b"0x01"),
            SupportedFeature.TOUCHMOUSE_RAW_POINTS,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x10, data=b"0x01"),
            SupportedFeature.TOUCHMOUSE_RAW_POINTS,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x05, data=b"0x01"),
            SupportedFeature.TOUCHMOUSE_RAW_POINTS,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x00, data=b"0x01"),
            SupportedFeature.REPROG_CONTROLS,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x02, data=b"0x01"),
            SupportedFeature.REPROG_CONTROLS,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x00, data=b"0x01"),
            SupportedFeature.BACKLIGHT2,
        ),
        (
            HIDPPNotification(
                0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x00, data=b"\x01\x01\x01\x01\x01\x01\x01\x01"
            ),
            SupportedFeature.REPROG_CONTROLS_V4,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x10, data=b"0x01"),
            SupportedFeature.REPROG_CONTROLS_V4,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x20, data=b"0x01"),
            SupportedFeature.REPROG_CONTROLS_V4,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x00, data=b"0x01"),
            SupportedFeature.HIRES_WHEEL,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x10, data=b"0x01"),
            SupportedFeature.HIRES_WHEEL,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x02, data=b"0x01"),
            SupportedFeature.HIRES_WHEEL,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x00, data=b"0x01"),
            SupportedFeature.ONBOARD_PROFILES,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x20, data=b"0x01"),
            SupportedFeature.ONBOARD_PROFILES,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x00, data=b"0x01"),
            SupportedFeature.BRIGHTNESS_CONTROL,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x10, data=b"0x01"),
            SupportedFeature.BRIGHTNESS_CONTROL,
        ),
        (
            HIDPPNotification(0, 0, sub_id=Notification.CONNECT_DISCONNECT, address=0x20, data=b"0x01"),
            SupportedFeature.BRIGHTNESS_CONTROL,
        ),
    ],
)
def test_process_feature_notification(mocker, hidpp_notification, feature):
    fake_device = fake_hidpp.Device()
    fake_device.receiver = ["rec1", "rec2"]

    result = notifications._process_feature_notification(fake_device, hidpp_notification, feature)

    assert result is True
