from logitech_receiver import hidpp10
from logitech_receiver import hidpp10_constants
from logitech_receiver.hidpp10_constants import Registers

_hidpp10 = hidpp10.Hidpp10()


def test_read_register(device_hidpp10):
    result = hidpp10.read_register(
        device_hidpp10,
        register=Registers.BATTERY_STATUS,
    )

    assert result == hidpp10_constants.NotificationFlag(int("000900", 16))


def test_set_notification_flags(mocker, device_hidpp10):
    spy_request = mocker.spy(device_hidpp10, "request")

    result = _hidpp10.set_notification_flags(
        device_hidpp10,
        hidpp10_constants.NotificationFlag.BATTERY_STATUS,
        hidpp10_constants.NotificationFlag.WIRELESS,
    )

    spy_request.assert_called_once_with(0x8000 | Registers.NOTIFICATIONS, b"\x10\x01\x00")
    assert result is not None
