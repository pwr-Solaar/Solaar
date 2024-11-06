from unittest import mock

from solaar.ui import desktop_notifications


def test_notifications_available():
    result = desktop_notifications.notifications_available()

    assert not result


def test_init():
    assert not desktop_notifications.init()


def test_uninit():
    assert desktop_notifications.uninit() is None


def test_alert():
    reason = "unknown"
    assert desktop_notifications.alert(reason) is None


def test_show():
    dev = mock.MagicMock()
    reason = "unknown"
    assert desktop_notifications.show(dev, reason) is None
