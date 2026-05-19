from unittest import mock

from solaar.ui import desktop_notifications

# The mock_desktop_notifications autouse fixture (tests/conftest.py) swaps the
# libnotify backend for a mock, so these exercise the real code paths without
# raising real desktop notifications.


def test_init():
    result = desktop_notifications.init()

    assert result == desktop_notifications.available


def test_uninit():
    assert desktop_notifications.uninit() is None


def test_alert(mock_desktop_notifications):
    assert desktop_notifications.alert("unknown") is None

    if desktop_notifications.available:
        mock_desktop_notifications.Notification.return_value.show.assert_called()


class MockDevice(mock.Mock):
    name = "MockDevice"

    def close():
        return True


def test_show(mock_desktop_notifications):
    result = desktop_notifications.show(MockDevice(), "unknown")

    if desktop_notifications.available:
        assert result is not None
        mock_desktop_notifications.Notification.return_value.show.assert_called()
    else:
        assert result is None
