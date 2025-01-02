from unittest import mock

from solaar.ui import desktop_notifications

# depends on external environment, so make some tests dependent on availability


def test_init():
    result = desktop_notifications.init()

    assert result == desktop_notifications.available


def test_uninit():
    assert desktop_notifications.uninit() is None


def test_alert():
    reason = "unknown"
    assert desktop_notifications.alert(reason) is None


class MockDevice(mock.Mock):
    name = "MockDevice"

    def close():
        return True


def test_show():
    dev = MockDevice()
    reason = "unknown"
    available = desktop_notifications.init()

    result = desktop_notifications.show(dev, reason)
    if available:
        assert result is not None
    else:
        assert result is None
