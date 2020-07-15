# -*- python-mode -*-
# -*- coding: UTF-8 -*-

## Copyright (C) 2012-2013  Daniel Pavel
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with this program; if not, write to the Free Software Foundation, Inc.,
## 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from __future__ import absolute_import, division, print_function, unicode_literals

from threading import Timer as _Timer

from gi.repository import GLib, Gtk
from logitech_receiver.settings import KIND as _SETTING_KIND
from solaar.i18n import _
from solaar.ui import ui_async as _ui_async

#
#
#


def _read_async(setting, force_read, sbox, device_is_online):
    def _do_read(s, force, sb, online):
        v = s.read(not force)
        GLib.idle_add(_update_setting_item, sb, v, online, priority=99)

    _ui_async(_do_read, setting, force_read, sbox, device_is_online)


def _write_async(setting, value, sbox):
    _ignore, failed, spinner, control = sbox.get_children()
    control.set_sensitive(False)
    failed.set_visible(False)
    spinner.set_visible(True)
    spinner.start()

    def _do_write(s, v, sb):
        v = setting.write(v)
        GLib.idle_add(_update_setting_item, sb, v, True, priority=99)

    _ui_async(_do_write, setting, value, sbox)


def _write_async_key_value(setting, key, value, sbox):
    _ignore, failed, spinner, control = sbox.get_children()
    control.set_sensitive(False)
    failed.set_visible(False)
    spinner.set_visible(True)
    spinner.start()

    def _do_write_key_value(s, k, v, sb):
        v = setting.write_key_value(k, v)
        GLib.idle_add(_update_setting_item, sb, {k: v}, True, priority=99)

    _ui_async(_do_write_key_value, setting, key, value, sbox)


#
#
#


def _create_toggle_control(setting):
    def _switch_notify(switch, _ignore, s):
        if switch.get_sensitive():
            _write_async(s, switch.get_active() is True, switch.get_parent())

    c = Gtk.Switch()
    c.connect('notify::active', _switch_notify, setting)
    return c


def _create_choice_control(setting):
    def _combo_notify(cbbox, s):
        if cbbox.get_sensitive():
            _write_async(s, cbbox.get_active_id(), cbbox.get_parent())

    c = Gtk.ComboBoxText()
    # TODO i18n text entries
    for entry in setting.choices:
        c.append(str(int(entry)), str(entry))
    c.connect('changed', _combo_notify, setting)
    return c


def _create_map_choice_control(setting):
    def _map_value_notify_key(cbbox, s):
        setting, valueBox = s
        key_choice = int(cbbox.get_active_id())
        if cbbox.get_sensitive():
            valueBox.remove_all()
            _map_populate_value_box(valueBox, setting, key_choice)

    def _map_value_notify_value(cbbox, s):
        setting, keyBox = s
        key_choice = keyBox.get_active_id()
        if key_choice is not None and cbbox.get_sensitive() and cbbox.get_active_id():
            if setting._value.get(key_choice) != int(cbbox.get_active_id()):
                setting._value[key_choice] = int(cbbox.get_active_id())
                _write_async_key_value(setting, key_choice, setting._value[key_choice], cbbox.get_parent().get_parent())

    def _map_populate_value_box(valueBox, setting, key_choice):
        choices = None
        choices = setting.choices[key_choice]
        current = setting._value.get(str(key_choice)) if setting._value else None
        if choices:
            # TODO i18n text entries
            for choice in choices:
                valueBox.append(str(int(choice)), str(choice))
            if current is not None:
                valueBox.set_active_id(str(int(current)))

    c = Gtk.HBox(homogeneous=False, spacing=6)
    keyBox = Gtk.ComboBoxText()
    valueBox = Gtk.ComboBoxText()
    c.pack_start(keyBox, False, False, 0)
    c.pack_end(valueBox, False, False, 0)
    # TODO i18n text entries
    for entry in setting.choices:
        keyBox.append(str(int(entry)), str(entry))
    keyBox.set_active(0)
    keyBox.connect('changed', _map_value_notify_key, (setting, valueBox))
    _map_populate_value_box(valueBox, setting, int(keyBox.get_active_id()))
    valueBox.connect('changed', _map_value_notify_value, (setting, keyBox))
    return c


def _create_slider_control(setting):
    class SliderControl:
        __slots__ = ('gtk_range', 'timer', 'setting')

        def __init__(self, setting):
            self.setting = setting
            self.timer = None

            self.gtk_range = Gtk.Scale()
            self.gtk_range.set_range(*self.setting.range)
            self.gtk_range.set_round_digits(0)
            self.gtk_range.set_digits(0)
            self.gtk_range.set_increments(1, 5)
            self.gtk_range.connect('value-changed', lambda _, c: c._changed(), self)

        def _write(self):
            _write_async(self.setting, int(self.gtk_range.get_value()), self.gtk_range.get_parent())
            self.timer.cancel()

        def _changed(self):
            if self.gtk_range.get_sensitive():
                if self.timer:
                    self.timer.cancel()
                self.timer = _Timer(0.5, lambda: GLib.idle_add(self._write))
                self.timer.start()

    control = SliderControl(setting)
    return control.gtk_range


#
#
#


def _create_sbox(s):
    sbox = Gtk.HBox(homogeneous=False, spacing=6)
    sbox.pack_start(Gtk.Label(s.label), False, False, 0)

    spinner = Gtk.Spinner()
    spinner.set_tooltip_text(_('Working') + '...')

    failed = Gtk.Image.new_from_icon_name('dialog-warning', Gtk.IconSize.SMALL_TOOLBAR)
    failed.set_tooltip_text(_('Read/write operation failed.'))

    if s.kind == _SETTING_KIND.toggle:
        control = _create_toggle_control(s)
        sbox.pack_end(control, False, False, 0)
    elif s.kind == _SETTING_KIND.choice:
        control = _create_choice_control(s)
        sbox.pack_end(control, False, False, 0)
    elif s.kind == _SETTING_KIND.range:
        control = _create_slider_control(s)
        sbox.pack_end(control, True, True, 0)
    elif s.kind == _SETTING_KIND.map_choice:
        control = _create_map_choice_control(s)
        sbox.pack_end(control, True, True, 0)
    elif s.kind == _SETTING_KIND.multiple_toggle:
        # ugly temporary hack!
        choices = {k: [False, True] for k in s._validator.options}

        class X:
            def __init__(self, obj, ext):
                self.obj = obj
                self.ext = ext

            def __getattr__(self, attr):
                try:
                    return self.ext[attr]
                except KeyError:
                    return getattr(self.obj, attr)

        control = _create_map_choice_control(X(s, {'choices': choices}))
        sbox.pack_end(control, True, True, 0)
    else:
        raise Exception('NotImplemented')

    control.set_sensitive(False)  # the first read will enable it
    sbox.pack_end(spinner, False, False, 0)
    sbox.pack_end(failed, False, False, 0)

    if s.description:
        sbox.set_tooltip_text(s.description)

    sbox.show_all()
    spinner.start()  # the first read will stop it
    failed.set_visible(False)

    return sbox


def _update_setting_item(sbox, value, is_online=True):
    _ignore, failed, spinner, control = sbox.get_children()  # depends on box layout
    spinner.set_visible(False)
    spinner.stop()

    if value is None:
        control.set_sensitive(False)
        failed.set_visible(is_online)
        return

    control.set_sensitive(False)
    failed.set_visible(False)
    if isinstance(control, Gtk.Switch):
        control.set_active(value)
    elif isinstance(control, Gtk.ComboBoxText):
        control.set_active_id(str(int(value)))
    elif isinstance(control, Gtk.Scale):
        control.set_value(int(value))
    elif isinstance(control, Gtk.HBox):
        kbox, vbox = control.get_children()  # depends on box layout
        if value.get(kbox.get_active_id()):
            vbox.set_active_id(str(value.get(kbox.get_active_id())))
    else:
        raise Exception('NotImplemented')
    control.set_sensitive(True)


#
#
#

# config panel
_box = None
_items = {}


def create():
    global _box
    assert _box is None
    _box = Gtk.VBox(homogeneous=False, spacing=8)
    _box._last_device = None
    return _box


def update(device, is_online=None):
    assert _box is not None
    assert device
    device_id = (device.receiver.path, device.number)
    if is_online is None:
        is_online = bool(device.online)

    # if the device changed since last update, clear the box first
    if device_id != _box._last_device:
        _box.set_visible(False)
        _box._last_device = device_id

    # hide controls belonging to other devices
    for k, sbox in _items.items():
        sbox = _items[k]
        sbox.set_visible(k[0:2] == device_id)

    for s in device.settings:
        k = (device_id[0], device_id[1], s.name)
        if k in _items:
            sbox = _items[k]
        else:
            sbox = _items[k] = _create_sbox(s)
            _box.pack_start(sbox, False, False, 0)

        _read_async(s, False, sbox, is_online)

    _box.set_visible(True)


def clean(device):
    """Remove the controls for a given device serial.
    Needed after the device has been unpaired.
    """
    assert _box is not None
    device_id = (device.receiver.path, device.number)
    for k in list(_items.keys()):
        if k[0:2] == device_id:
            _box.remove(_items[k])
            del _items[k]


def destroy():
    global _box
    _box = None
    _items.clear()
