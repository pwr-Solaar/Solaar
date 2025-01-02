from unittest import mock

from logitech_receiver import desktop_notifications

# depends on external environment, so make some tests dependent on availability


def test_init():
    result = desktop_notifications.init()

    assert result == desktop_notifications.available


def test_uninit():
    assert desktop_notifications.uninit() is None


class MockDevice(mock.Mock):
    name = "MockDevice"

    def close():
        return True


def test_show():
    dev = MockDevice()
    reason = "unknown"
    result = desktop_notifications.show(dev, reason)
    assert result is not None if desktop_notifications.available else result is None
