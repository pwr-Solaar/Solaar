from unittest import mock

import gi
import pytest

from logitech_receiver import settings
from solaar.ui import config_panel
from solaar.ui import window

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # NOQA: E402

gtk_init = Gtk.init_check()[0]


class FakeValidator:
    readable = True


class FakeDevice:
    def __init__(self, persister=None):
        self.online = False
        self.persister = persister
        self.settings = []
        self.receiver = None
        self.path = "/dev/fake"
        self.number = 1


class FakeSetting:
    def __init__(self, device, name="dpi", kind=settings.Kind.TOGGLE):
        self.name = name
        self.kind = kind
        self.display = True
        self.description = ""
        self.label = name
        self.persist = True
        self._value = None
        self._device = device
        self._validator = FakeValidator()


class FakeBattery:
    level = 50
    voltage = None
    light_level = None
    next_level = None

    def charging(self):
        return False


class FakeReceiver:
    may_unpair = False


def _lock_button(sbox):
    return sbox._change_icon.get_parent()


def _blocked(widget):
    """True when the widget or one of its ancestors is insensitive, which is what
    makes clicking it unreachable."""
    while widget is not None:
        if not widget.get_sensitive():
            return True
        widget = widget.get_parent()
    return False


@pytest.fixture
def sbox():
    device = FakeDevice()
    box = config_panel._create_sbox(FakeSetting(device), device)
    config_panel._items[(device.path, device.number, "dpi")] = box
    yield box
    config_panel.destroy()


@pytest.mark.skipif(not gtk_init, reason="requires Gtk")
def test_offline_device_greys_value_widget_only(sbox):
    config_panel._update_setting_item(sbox, True, is_online=False, sensitive=True)

    assert not sbox._control.get_sensitive()
    assert _lock_button(sbox).get_sensitive()


@pytest.mark.skipif(not gtk_init, reason="requires Gtk")
def test_online_device_enables_value_widget_and_lock(sbox):
    config_panel._update_setting_item(sbox, True, is_online=True, sensitive=True)

    assert sbox._control.get_sensitive()
    assert _lock_button(sbox).get_sensitive()


@pytest.mark.skipif(not gtk_init, reason="requires Gtk")
def test_locked_setting_keeps_lock_clickable_while_offline(sbox):
    """A "no changes allowed" lock is a user choice, so its lock stays clickable."""
    config_panel._update_setting_item(sbox, True, is_online=False, sensitive=False)

    assert not sbox._control.get_sensitive()
    assert _lock_button(sbox).get_sensitive()


@pytest.mark.skipif(not gtk_init, reason="requires Gtk")
def test_unlocking_an_ignored_setting_offline_does_not_contact_device(sbox):
    """Toggling the lock out of "ignore" while asleep only records the choice.

    The write happens on the next config_panel.update() once the device is
    online; contacting an asleep device here can only fail."""
    persister = mock.MagicMock()
    persister.get.return_value = True
    sbox.setting._device.persister = persister
    sbox.setting._device.settings = [sbox.setting]
    config_panel._change_icon(settings.SENSITIVITY_IGNORE, sbox._change_icon)

    with mock.patch.object(config_panel, "_write_async") as write, mock.patch.object(config_panel, "_read_async") as read:
        config_panel._change_click(_lock_button(sbox), sbox)

    write.assert_not_called()
    read.assert_not_called()
    persister.set_sensitivity.assert_called_once_with("dpi", True)
    assert sbox._change_icon._allowed is True


@pytest.mark.skipif(not gtk_init, reason="requires Gtk")
def test_unlocking_an_ignored_setting_online_resyncs(sbox):
    persister = mock.MagicMock()
    persister.get.return_value = True
    sbox.setting._device.persister = persister
    sbox.setting._device.settings = [sbox.setting]
    sbox.setting._device.online = True
    config_panel._change_icon(settings.SENSITIVITY_IGNORE, sbox._change_icon)

    with mock.patch.object(config_panel, "_write_async") as write:
        config_panel._change_click(_lock_button(sbox), sbox)

    write.assert_called_once_with(sbox.setting, True, sbox)
    assert sbox._change_icon._allowed is True


@pytest.mark.skipif(not gtk_init, reason="requires Gtk")
def test_offline_device_panel_keeps_lock_reachable():
    """The reported symptom: an asleep device greyed the whole device panel out,
    and because the lock buttons live in that panel they couldn't be clicked, so
    a setting could neither be changed nor unlocked until the device woke up."""
    config_panel.destroy()
    device = FakeDevice()
    device.battery_info = FakeBattery()
    device.link_encrypted = True
    device.receiver = FakeReceiver()
    setting = FakeSetting(device)
    device.settings = [setting]

    panel = window._create_device_panel()
    buttons = window._create_buttons_box()
    sbox = config_panel._create_sbox(setting, device)
    config_panel._box.pack_start(sbox, False, False, 0)
    config_panel._update_setting_item(sbox, True, is_online=False, sensitive=True)

    window._update_device_panel(device, panel, buttons)

    assert not sbox._control.get_sensitive()
    assert not _blocked(_lock_button(sbox))
