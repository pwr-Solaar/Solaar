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

from gi.repository import Gdk, GLib, Gtk
from logitech_receiver.settings import KIND as _SETTING_KIND
from solaar.i18n import _, ngettext
from solaar.ui import ui_async as _ui_async

#
#
#


def _read_async(setting, force_read, sbox, device_is_online, sensitive):
    def _do_read(s, force, sb, online, sensitive):
        v = s.read(not force)
        GLib.idle_add(_update_setting_item, sb, v, online, sensitive, priority=99)

    _ui_async(_do_read, setting, force_read, sbox, device_is_online, sensitive)


def _write_async(setting, value, sbox):
    failed, spinner, control = _get_failed_spinner_control(sbox)
    control.set_sensitive(False)
    failed.set_visible(False)
    spinner.set_visible(True)
    spinner.start()

    def _do_write(s, v, sb):
        v = setting.write(v)
        GLib.idle_add(_update_setting_item, sb, v, True, priority=99)

    _ui_async(_do_write, setting, value, sbox)


def _write_async_key_value(setting, key, value, sbox):
    failed, spinner, control = _get_failed_spinner_control(sbox)
    control.set_sensitive(False)
    failed.set_visible(False)
    spinner.set_visible(True)
    spinner.start()

    def _do_write_key_value(s, k, v, sb):
        v = setting.write_key_value(k, v)
        GLib.idle_add(_update_setting_item, sb, {k: v}, True, priority=99)

    _ui_async(_do_write_key_value, setting, key, value, sbox)


def _write_async_item_value(setting, item, value, sbox):
    failed, spinner, control = _get_failed_spinner_control(sbox)
    control.set_sensitive(False)
    failed.set_visible(False)
    spinner.set_visible(True)
    spinner.start()

    def _do_write_item_value(s, k, v, sb):
        v = setting.write_item_value(k, v)
        GLib.idle_add(_update_setting_item, sb, {k: v}, True, priority=99)

    _ui_async(_do_write_item_value, setting, item, value, sbox)


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


def _create_multiple_toggle_control(setting, change):
    def _toggle_notify(control, _, setting):
        if control.get_sensitive():
            key = control._setting_key
            new_state = control.get_active()
            if setting._value[key] != new_state:
                setting._value[key] = new_state
                p = control
                for _ in range(5):
                    p = p.get_parent()
                _write_async_key_value(setting, key, new_state, p)

    def _toggle_display(lb):
        lb._showing = not lb._showing
        if not lb._showing:
            for c in lb.get_children():
                c.hide()
            lb.hide()
        else:
            lb.show()
            for c in lb.get_children():
                c.show_all()

    lb = Gtk.ListBox()
    lb._toggle_display = (lambda l: (lambda: _toggle_display(l)))(lb)
    lb._showing = True
    lb.set_selection_mode(Gtk.SelectionMode.NONE)
    lb.set_no_show_all(True)
    lb._label_control_pairs = []
    btn = Gtk.Button('? / ?')
    for k in setting._validator.all_options():
        h = Gtk.HBox(homogeneous=False, spacing=0)
        lbl_text = str(k)
        lbl_tooltip = None
        if hasattr(setting, '_labels'):
            l1, l2 = setting._labels.get(k, (None, None))
            if l1:
                lbl_text = l1
            if l2:
                lbl_tooltip = l2
        lbl = Gtk.Label(lbl_text)
        h.set_tooltip_text(lbl_tooltip or ' ')
        control = Gtk.Switch()
        control._setting_key = str(int(k))
        control.connect('notify::active', _toggle_notify, setting)
        h.pack_start(lbl, False, False, 0)
        h.pack_end(control, False, False, 0)
        lbl.set_alignment(0.0, 0.5)
        lbl.set_margin_left(30)
        lb.add(h)
        lb._label_control_pairs.append((lbl, control))
    _disable_listbox_highlight_bg(lb)
    lb._toggle_display()
    btn.connect('clicked', lambda _: lb._toggle_display())

    hbox = Gtk.HBox(homogeneous=False, spacing=6)
    hbox.pack_end(change, False, False, 0)
    hbox.pack_end(btn, False, False, 0)
    btn.set_alignment(1.0, 0.5)
    vbox = Gtk.VBox(homogeneous=False, spacing=6)
    vbox.pack_start(hbox, True, True, 0)
    vbox.pack_end(lb, True, True, 0)
    vbox._header, vbox._button, vbox._control = hbox, btn, lb
    return vbox


def _create_multiple_range_control(setting, change):
    def _write(control, setting, item, sub_item):
        control._timer.cancel()
        delattr(control, '_timer')
        new_state = int(control.get_value())
        if setting._value[str(int(item))][str(sub_item)] != new_state:
            setting._value[str(int(item))][str(sub_item)] = new_state
            p = control
            for _i in range(7):
                p = p.get_parent()
            _write_async_item_value(setting, str(int(item)), setting._value[str(int(item))], p)

    def _changed(control, setting, item, sub_item):
        if control.get_sensitive():
            if hasattr(control, '_timer'):
                control._timer.cancel()
            control._timer = _Timer(0.5, lambda: GLib.idle_add(_write, control, setting, item, sub_item))
            control._timer.start()

    def _toggle_display(lb):
        lb._showing = not lb._showing
        if not lb._showing:
            for c in lb.get_children():
                c.hide()
            lb.hide()
        else:
            lb.show()
            for c in lb.get_children():
                c.show_all()

    lb = Gtk.ListBox()
    lb._toggle_display = (lambda l: (lambda: _toggle_display(l)))(lb)
    lb.set_selection_mode(Gtk.SelectionMode.NONE)
    lb._showing = True
    lb.set_no_show_all(True)
    lb._items = []
    btn = Gtk.Button('...')
    for item in setting._validator.items:
        lbl_text = str(item)
        lbl_tooltip = None
        if hasattr(setting, '_labels'):
            l1, l2 = setting._labels.get(item, (None, None))
            if l1:
                lbl_text = l1
            if l2:
                lbl_tooltip = l2
        item_lbl = Gtk.Label(lbl_text)
        lb.add(item_lbl)
        lb.set_tooltip_text(lbl_tooltip or ' ')
        item_lb = Gtk.ListBox()
        item_lb.set_selection_mode(Gtk.SelectionMode.NONE)
        item_lb._sub_items = []
        for sub_item in setting._validator.sub_items[item]:
            h = Gtk.HBox(homogeneous=False, spacing=20)
            lbl_text = str(sub_item)
            lbl_tooltip = None
            if hasattr(setting, '_labels_sub'):
                l1, l2 = setting._labels_sub.get(str(sub_item), (None, None))
                if l1:
                    lbl_text = l1
                if l2:
                    lbl_tooltip = l2
            sub_item_lbl = Gtk.Label(lbl_text)
            h.set_tooltip_text(lbl_tooltip or ' ')
            h.pack_start(sub_item_lbl, False, False, 0)
            sub_item_lbl.set_margin_left(30)
            sub_item_lbl.set_alignment(0.0, 0.5)
            if sub_item.widget == 'Scale':
                control = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, sub_item.minimum, sub_item.maximum, 1)
                control.set_round_digits(0)
                control.set_digits(0)
                h.pack_end(control, True, True, 0)
            elif sub_item.widget == 'SpinButton':
                control = Gtk.SpinButton.new_with_range(sub_item.minimum, sub_item.maximum, 1)
                control.set_digits(0)
                h.pack_end(control, False, False, 0)
            else:
                raise NotImplementedError
            control.connect('value-changed', _changed, setting, item, sub_item)
            item_lb.add(h)
            h._setting_sub_item = sub_item
            h._label, h._control = sub_item_lbl, control
            item_lb._sub_items.append(h)
        item_lb._setting_item = item
        _disable_listbox_highlight_bg(item_lb)
        lb.add(item_lb)
        lb._items.append(item_lb)
    _disable_listbox_highlight_bg(lb)
    lb._toggle_display()
    btn.connect('clicked', lambda _: lb._toggle_display())
    btn.set_alignment(1.0, 0.5)
    hbox = Gtk.HBox(homogeneous=False, spacing=6)
    hbox.pack_end(change, False, False, 0)
    hbox.pack_end(btn, False, False, 0)
    vbox = Gtk.VBox(homogeneous=False, spacing=6)
    vbox.pack_start(hbox, True, True, 0)
    vbox.pack_end(lb, True, True, 0)
    vbox._header, vbox._button, vbox._control = hbox, btn, lb
    return vbox


#
#
#


# clicking on the lock icon changes the sensitivity of the setting
def _change_click(eb, button, arg):
    control, device, name = arg
    sensitive = not control.get_sensitive()
    control.set_sensitive(sensitive)
    icon = eb.get_children()[0]
    _change_icon(sensitive, icon)
    if device.persister:  # remember the new setting sensitivity
        device.persister.set_sensitivity(name, sensitive)
    return True


def _change_icon(allowed, icon):
    icon.set_from_icon_name('changes-allow' if allowed else 'changes-prevent', Gtk.IconSize.LARGE_TOOLBAR)
    icon.set_tooltip_text(_('Click to prevent changes.') if allowed else _('Click to allow changes.'))


def _create_sbox(s, device):
    sbox = Gtk.HBox(homogeneous=False, spacing=6)
    lbl = Gtk.Label(s.label)
    label = Gtk.EventBox()
    label.add(lbl)

    spinner = Gtk.Spinner()
    spinner.set_tooltip_text(_('Working') + '...')

    failed = Gtk.Image.new_from_icon_name('dialog-warning', Gtk.IconSize.SMALL_TOOLBAR)
    failed.set_tooltip_text(_('Read/write operation failed.'))

    change_icon = Gtk.Image.new_from_icon_name('changes-prevent', Gtk.IconSize.LARGE_TOOLBAR)
    _change_icon(False, change_icon)
    change = Gtk.EventBox()
    change.add(change_icon)

    if s.kind == _SETTING_KIND.toggle:
        control = _create_toggle_control(s)
    elif s.kind == _SETTING_KIND.choice:
        control = _create_choice_control(s)
    elif s.kind == _SETTING_KIND.range:
        control = _create_slider_control(s)
    elif s.kind == _SETTING_KIND.map_choice:
        control = _create_map_choice_control(s)
    elif s.kind == _SETTING_KIND.multiple_toggle:
        vbox = _create_multiple_toggle_control(s, change)
        control = vbox._control
        lbl.set_alignment(0.0, 0.5)
        sbox.pack_start(vbox, True, True, 0)
    elif s.kind == _SETTING_KIND.multiple_range:
        vbox = _create_multiple_range_control(s, change)
        control = vbox._control
        lbl.set_alignment(0.0, 0.5)
        sbox.pack_start(vbox, True, True, 0)
    else:
        raise Exception('NotImplemented')
    control.set_sensitive(False)  # the first read will enable it
    control.kind = s.kind

    change.set_sensitive(True)
    change.connect('button-press-event', _change_click, (control, device, s.name))

    if s.kind in [_SETTING_KIND.multiple_toggle, _SETTING_KIND.multiple_range]:
        vbox._header.pack_start(label, False, False, 0)
        vbox._header.pack_end(spinner, False, False, 0)
        vbox._header.pack_end(failed, False, False, 0)
        sbox._button = vbox._button
    else:
        sbox.pack_start(label, False, False, 0)
        sbox.pack_end(change, False, False, 0)
        sbox.pack_end(control, s.kind == _SETTING_KIND.range, s.kind == _SETTING_KIND.range, 0)
        sbox.pack_end(spinner, False, False, 0)
        sbox.pack_end(failed, False, False, 0)
    sbox._label = label
    sbox._lbl = lbl
    sbox._spinner = spinner
    sbox._failed = failed
    sbox._change = change
    sbox._change_icon = change_icon
    sbox._control = control

    if s.description:
        sbox.set_tooltip_text(s.description)

    sbox.show_all()

    spinner.start()  # the first read will stop it
    failed.set_visible(False)

    return sbox


def _update_setting_item(sbox, value, is_online=True, sensitive=True):
    failed, spinner, control = _get_failed_spinner_control(sbox)
    spinner.set_visible(False)
    spinner.stop()

    if value is None:
        control.set_sensitive(False)
        _change_icon(False, sbox._change_icon)
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
    elif isinstance(control, Gtk.ListBox):
        if control.kind == _SETTING_KIND.multiple_toggle:
            total = len(control._label_control_pairs)
            active = 0
            to_join = []
            for lbl, elem in control._label_control_pairs:
                v = value.get(elem._setting_key, None)
                if v is not None:
                    elem.set_active(v)
                if elem.get_active():
                    active += 1
                to_join.append(lbl.get_text() + ': ' + str(elem.get_active()))
            b = ', '.join(to_join)
            sbox._button.set_label(f'{active} / {total}')
            sbox._button.set_tooltip_text(b)
        elif control.kind == _SETTING_KIND.multiple_range:
            b = ''
            n = 0
            for ch in control._items:
                # item
                item = ch._setting_item
                v = value.get(str(int(item)), None)
                if v is not None:
                    b += str(item) + ': ('
                    to_join = []
                    for c in ch._sub_items:
                        # sub-item
                        sub_item = c._setting_sub_item
                        c._control.set_value(v[str(sub_item)])
                        n += 1
                        to_join.append(str(sub_item) + f'={v[str(sub_item)]}')
                    b += ', '.join(to_join) + ') '
                lbl_text = ngettext('%d value', '%d values', n) % n
                sbox._button.set_label(lbl_text)
                sbox._button.set_tooltip_text(b)
        else:
            raise NotImplementedError
    else:
        raise Exception('NotImplemented')

    control.set_sensitive(sensitive)
    _change_icon(sensitive, sbox._change_icon)


def _get_failed_spinner_control(sbox):
    return sbox._failed, sbox._spinner, sbox._control


def _disable_listbox_highlight_bg(lb):
    colour = Gdk.RGBA()
    colour.parse('rgba(0,0,0,0)')
    for child in lb.get_children():
        child.override_background_color(Gtk.StateFlags.PRELIGHT, colour)


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
    device_id = (device.receiver.path if device.receiver else device.path, device.number)
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
            sbox = _items[k] = _create_sbox(s, device)
            _box.pack_start(sbox, False, False, 0)

        sensitive = device.persister.get_sensitivity(s.name) if device.persister else True
        _read_async(s, False, sbox, is_online, sensitive)

    _box.set_visible(True)


def clean(device):
    """Remove the controls for a given device serial.
    Needed after the device has been unpaired.
    """
    assert _box is not None
    device_id = (device.receiver.path if device.receiver else device.path, device.number)
    for k in list(_items.keys()):
        if k[0:2] == device_id:
            _box.remove(_items[k])
            del _items[k]


def destroy():
    global _box
    _box = None
    _items.clear()
