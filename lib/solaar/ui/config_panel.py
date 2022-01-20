# -*- python-mode -*-

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

from threading import Timer as _Timer

from gi.repository import Gdk, GLib, Gtk
from logitech_receiver.settings import KIND as _SETTING_KIND
from logitech_receiver.settings import SENSITIVITY_IGNORE as _SENSITIVITY_IGNORE
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


def _write_async(setting, value, sbox, sensitive=True, key=None):
    def _do_write(s, v, sb, key):
        try:
            if key is None:
                v = setting.write(v)
            else:
                v = setting.write_key_value(key, v)
                v = {key: v}
        except Exception:
            v = None
        if sb:
            GLib.idle_add(_update_setting_item, sb, v, True, sensitive, priority=99)

    if sbox:
        sbox._control.set_sensitive(False)
        sbox._failed.set_visible(False)
        sbox._spinner.set_visible(True)
        sbox._spinner.start()
    _ui_async(_do_write, setting, value, sbox, key)


#
#
#


class Control():
    def __init__(**kwargs):
        pass

    def init(self, sbox, delegate):
        self.sbox = sbox
        self.delegate = delegate if delegate else self

    def changed(self, *args):
        if self.get_sensitive():
            self.delegate.update()

    def update(self):
        _write_async(self.sbox.setting, self.get_value(), self.sbox)

    def layout(self, sbox, label, change, spinner, failed):
        sbox.pack_start(label, False, False, 0)
        sbox.pack_end(change, False, False, 0)
        sbox.pack_end(self, sbox.setting.kind == _SETTING_KIND.range, sbox.setting.kind == _SETTING_KIND.range, 0)
        sbox.pack_end(spinner, False, False, 0)
        sbox.pack_end(failed, False, False, 0)
        return self


class ToggleControl(Gtk.Switch, Control):
    def __init__(self, sbox, delegate=None):
        super().__init__(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.init(sbox, delegate)
        self.connect('notify::active', self.changed)

    def set_value(self, value):
        self.set_state(value)

    def get_value(self):
        return self.get_state()


class SliderControl(Gtk.Scale, Control):
    def __init__(self, sbox, delegate=None):
        super().__init__(halign=Gtk.Align.FILL)
        self.init(sbox, delegate)
        self.timer = None
        self.set_range(*self.sbox.setting.range)
        self.set_round_digits(0)
        self.set_digits(0)
        self.set_increments(1, 5)
        self.connect('value-changed', self.changed)

    def get_value(self):
        return int(super().get_value())

    def changed(self, *args):
        if self.get_sensitive():
            if self.timer:
                self.timer.cancel()
            self.timer = _Timer(0.5, lambda: GLib.idle_add(self.do_change))
            self.timer.start()

    def do_change(self):
        self.timer.cancel()
        self.update()


def _create_choice_control(sbox, delegate=None, choices=None):
    if 50 > len(choices if choices else sbox.setting.choices):
        return ChoiceControlLittle(sbox, choices=choices, delegate=delegate)
    else:
        return ChoiceControlBig(sbox, choices=choices, delegate=delegate)


class ChoiceControlLittle(Gtk.ComboBoxText, Control):
    def __init__(self, sbox, delegate=None, choices=None):
        super().__init__(halign=Gtk.Align.FILL)
        self.init(sbox, delegate)
        self.choices = choices if choices is not None else sbox.setting.choices
        for entry in self.choices:
            self.append(str(int(entry)), str(entry))
        self.connect('changed', self.changed)

    def get_value(self):
        return int(self.get_active_id()) if self.get_active_id() is not None else None

    def set_value(self, value):
        self.set_active_id(str(int(value)))

    def get_choice(self):
        id = self.get_value()
        return next((x for x in self.choices if x == id), None)

    def set_choices(self, choices):
        self.remove_all()
        for choice in choices:
            self.append(str(int(choice)), _(str(choice)))


class ChoiceControlBig(Gtk.Entry, Control):
    def __init__(self, sbox, delegate=None, choices=None):
        super().__init__(halign=Gtk.Align.FILL)
        self.init(sbox, delegate)
        self.choices = choices if choices is not None else sbox.setting.choices
        self.value = None
        self.set_width_chars(max([len(str(x)) for x in self.choices]) + 2)
        liststore = Gtk.ListStore(int, str)
        for v in self.choices:
            liststore.append((int(v), str(v)))
        completion = Gtk.EntryCompletion()
        completion.set_model(liststore)
        norm = lambda s: s.replace('_', '').replace(' ', '').lower()
        completion.set_match_func(lambda completion, key, it: norm(key) in norm(completion.get_model()[it][1]))
        completion.set_text_column(1)
        self.set_completion(completion)
        self.connect('changed', self.changed)
        self.connect('activate', self.activate)
        completion.connect('match_selected', self.select)

    def get_value(self):
        choice = self.get_choice()
        return int(choice) if choice is not None else None

    def set_value(self, value):
        self.set_text(str(next((x for x in self.choices if x == value), None)))

    def get_choice(self):
        key = self.get_text()
        return next((x for x in self.choices if x == key), None)

    def changed(self, *args):
        self.value = self.get_choice()
        icon = 'dialog-warning' if self.value is None else 'dialog-question' if self.get_sensitive() else ''
        self.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)
        tooltip = _('Incomplete') if self.value is None else _('Complete - ENTER to change')
        self.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, tooltip)

    def activate(self, *args):
        if self.value is not None and self.get_sensitive():
            self.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, '')
            self.delegate.update()

    def select(self, completion, model, iter):
        self.set_value(model.get(iter, 0)[0])
        if self.value and self.get_sensitive():
            self.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, '')
            self.delegate.update()


class MapChoiceControl(Gtk.HBox, Control):
    def __init__(self, sbox, delegate=None):
        super().__init__(homogeneous=False, spacing=6)
        self.init(sbox, delegate)
        self.keyBox = Gtk.ComboBoxText()
        for entry in sbox.setting.choices:
            self.keyBox.append(str(int(entry)), _(str(entry)))
        self.keyBox.set_active(0)
        key_choice = int(self.keyBox.get_active_id())
        self.value_choices = self.sbox.setting.choices[key_choice]
        self.valueBox = _create_choice_control(sbox.setting, choices=self.value_choices, delegate=self)
        self.pack_start(self.keyBox, False, False, 0)
        self.pack_end(self.valueBox, False, False, 0)
        self.keyBox.connect('changed', self.map_value_notify_key)

    def get_value(self):
        key_choice = self.keyBox.get_active_id()
        if key_choice is not None and self.valueBox.get_value() is not None:
            return self.valueBox.get_value()

    def set_value(self, value):
        self.valueBox.set_sensitive(self.get_sensitive())
        if value.get(self.keyBox.get_active_id()) is not None:
            self.valueBox.set_value(value.get(self.keyBox.get_active_id()))
        self.valueBox.set_sensitive(True)

    def map_populate_value_box(self, key_choice):
        choices = self.sbox.setting.choices[int(key_choice)]
        if choices != self.value_choices:
            self.value_choices = choices
            self.valueBox.remove_all()
            self.valueBox.set_choices(choices)
        current = self.sbox.setting._value.get(str(key_choice)) if self.sbox.setting._value else None
        if current is not None:
            self.valueBox.set_value(current)

    def map_value_notify_key(self, *args):
        key_choice = self.keyBox.get_active_id()
        if self.keyBox.get_sensitive():
            self.map_populate_value_box(key_choice)

    def update(self):
        key_choice = self.keyBox.get_active_id()
        value = self.get_value()
        if value is not None and self.valueBox.get_sensitive() and self.sbox.setting._value.get(key_choice) != value:
            self.sbox.setting._value[key_choice] = value
            _write_async(self.sbox.setting, value, self.sbox, key=key_choice)


class MultipleControl(Control):
    def layout(self, sbox, label, change, spinner, failed):
        self._header.pack_start(label, False, False, 0)
        self._header.pack_end(spinner, False, False, 0)
        self._header.pack_end(failed, False, False, 0)
        sbox.pack_start(self.vbox, True, True, 0)
        sbox._button = self._button
        return True

    def toggle_display(self, *args):
        self._showing = not self._showing
        if not self._showing:
            for c in self.get_children():
                c.hide()
            self.hide()
        else:
            self.show()
            for c in self.get_children():
                c.show_all()


class MultipleToggleControl(Gtk.ListBox, MultipleControl):
    def __init__(self, sbox, change, delegate=None):
        super().__init__()
        self.init(sbox, delegate)
        self.set_selection_mode(Gtk.SelectionMode.NONE)
        self.set_no_show_all(True)
        self._showing = True
        self._label_control_pairs = []
        for k in sbox.setting._validator.get_options():
            h = Gtk.HBox(homogeneous=False, spacing=0)
            lbl_text = str(k)
            lbl_tooltip = None
            if hasattr(sbox.setting, '_labels'):
                l1, l2 = sbox.setting._labels.get(k, (None, None))
                lbl_text = l1 if l1 else lbl_text
                lbl_tooltip = l2 if l2 else lbl_tooltip
            lbl = Gtk.Label(lbl_text)
            h.set_tooltip_text(lbl_tooltip or ' ')
            control = Gtk.Switch()
            control._setting_key = str(int(k))
            control.connect('notify::active', self.toggle_notify)
            h.pack_start(lbl, False, False, 0)
            h.pack_end(control, False, False, 0)
            lbl.set_alignment(0.0, 0.5)
            lbl.set_margin_left(30)
            self.add(h)
            self._label_control_pairs.append((lbl, control))
        btn = Gtk.Button('? / ?')
        btn.set_alignment(1.0, 0.5)
        btn.connect('clicked', self.toggle_display)
        self._button = btn
        hbox = Gtk.HBox(homogeneous=False, spacing=6)
        hbox.pack_end(change, False, False, 0)
        hbox.pack_end(btn, False, False, 0)
        self._header = hbox
        vbox = Gtk.VBox(homogeneous=False, spacing=6)
        vbox.pack_start(hbox, True, True, 0)
        vbox.pack_end(self, True, True, 0)
        self.vbox = vbox
        self.toggle_display()
        _disable_listbox_highlight_bg(self)

    def toggle_notify(self, switch, active):
        if switch.get_sensitive():
            key = switch._setting_key
            new_state = switch.get_state()
            if self.sbox.setting._value[key] != new_state:
                self.sbox.setting._value[key] = new_state
                _write_async(self.sbox.setting, new_state, self.sbox, key=key)

    def set_value(self, value):
        active = 0
        total = len(self._label_control_pairs)
        to_join = []
        for lbl, elem in self._label_control_pairs:
            v = value.get(elem._setting_key, None)
            if v is not None:
                elem.set_state(v)
            if elem.get_state():
                active += 1
            to_join.append(lbl.get_text() + ': ' + str(elem.get_state()))
        b = ', '.join(to_join)
        self._button.set_label(f'{active} / {total}')
        self._button.set_tooltip_text(b)


class MultipleRangeControl(Gtk.ListBox, MultipleControl):
    def __init__(self, sbox, change, delegate=None):
        super().__init__()
        self.init(sbox, delegate)
        self.set_selection_mode(Gtk.SelectionMode.NONE)
        self.set_no_show_all(True)
        self._showing = True
        self._items = []
        for item in sbox.setting._validator.items:
            lbl_text = str(item)
            lbl_tooltip = None
            if hasattr(sbox.setting, '_labels'):
                l1, l2 = sbox.setting._labels.get(int(item), (None, None))
                lbl_text = l1 if l1 else lbl_text
                lbl_tooltip = l2 if l2 else lbl_tooltip
            item_lbl = Gtk.Label(lbl_text)
            self.add(item_lbl)
            self.set_tooltip_text(lbl_tooltip or ' ')
            item_lb = Gtk.ListBox()
            item_lb.set_selection_mode(Gtk.SelectionMode.NONE)
            item_lb._sub_items = []
            for sub_item in sbox.setting._validator.sub_items[item]:
                h = Gtk.HBox(homogeneous=False, spacing=20)
                lbl_text = str(sub_item)
                lbl_tooltip = None
                if hasattr(sbox.setting, '_labels_sub'):
                    l1, l2 = sbox.setting._labels_sub.get(str(sub_item), (None, None))
                    lbl_text = l1 if l1 else lbl_text
                    lbl_tooltip = l2 if l2 else lbl_tooltip
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
                control.connect('value-changed', self.changed, item, sub_item)
                item_lb.add(h)
                h._setting_sub_item = sub_item
                h._label, h._control = sub_item_lbl, control
                item_lb._sub_items.append(h)
            item_lb._setting_item = item
            _disable_listbox_highlight_bg(item_lb)
            self.add(item_lb)
            self._items.append(item_lb)
        btn = Gtk.Button('...')
        btn.set_alignment(1.0, 0.5)
        btn.set_alignment(1.0, 0.5)
        btn.connect('clicked', self.toggle_display)
        self._button = btn
        hbox = Gtk.HBox(homogeneous=False, spacing=6)
        hbox.pack_end(change, False, False, 0)
        hbox.pack_end(btn, False, False, 0)
        self._header = hbox
        vbox = Gtk.VBox(homogeneous=False, spacing=6)
        vbox.pack_start(hbox, True, True, 0)
        vbox.pack_end(self, True, True, 0)
        self.vbox = vbox
        self.toggle_display()
        _disable_listbox_highlight_bg(self)

    def changed(self, control, item, sub_item):
        if control.get_sensitive():
            if hasattr(control, '_timer'):
                control._timer.cancel()
            control._timer = _Timer(0.5, lambda: GLib.idle_add(self._write, control, item, sub_item))
            control._timer.start()

    def _write(self, control, item, sub_item):
        control._timer.cancel()
        delattr(control, '_timer')
        new_state = int(control.get_value())
        if self.sbox.setting._value[str(int(item))][str(sub_item)] != new_state:
            self.sbox.setting._value[str(int(item))][str(sub_item)] = new_state
            _write_async(self.sbox.setting, self.sbox.setting._value[str(int(item))], self.sbox, key=str(int(item)))

    def set_value(self, value):
        b = ''
        n = 0
        for ch in self._items:
            item = ch._setting_item
            v = value.get(str(int(item)), None)
            if v is not None:
                b += str(item) + ': ('
                to_join = []
                for c in ch._sub_items:
                    sub_item = c._setting_sub_item
                    try:
                        sub_item_value = v[str(sub_item)]
                    except KeyError:
                        sub_item_value = c._control.get_value()
                    c._control.set_value(sub_item_value)
                    n += 1
                    to_join.append(str(sub_item) + f'={sub_item_value}')
                b += ', '.join(to_join) + ') '
        lbl_text = ngettext('%d value', '%d values', n) % n
        self._button.set_label(lbl_text)
        self._button.set_tooltip_text(b)


#
#
#

_allowables_icons = {True: 'changes-allow', False: 'changes-prevent', _SENSITIVITY_IGNORE: 'dialog-error'}
_allowables_tooltips = {
    True: _('Changes allowed'),
    False: _('No changes allowed'),
    _SENSITIVITY_IGNORE: _('Ignore this setting')
}
_next_allowable = {True: False, False: _SENSITIVITY_IGNORE, _SENSITIVITY_IGNORE: True}
_icons_allowables = {v: k for k, v in _allowables_icons.items()}


# clicking on the lock icon changes from changeable to unchangeable to ignore
def _change_click(button, sbox):
    icon = button.get_children()[0]
    icon_name, _ = icon.get_icon_name()
    allowed = _icons_allowables.get(icon_name, True)
    new_allowed = _next_allowable[allowed]
    sbox._control.set_sensitive(new_allowed is True)
    _change_icon(new_allowed, icon)
    if sbox.setting._device.persister:  # remember the new setting sensitivity
        sbox.setting._device.persister.set_sensitivity(sbox.setting.name, new_allowed)
    if allowed == _SENSITIVITY_IGNORE:  # update setting if it was being ignored
        setting = next((s for s in sbox.setting._device.settings if s.name == sbox.setting.name), None)
        if setting:
            persisted = sbox.setting._device.persister.get(setting.name) if sbox.setting._device.persister else None
            if setting.persist and persisted is not None:
                _write_async(setting, persisted, sbox)
            else:
                _read_async(setting, True, sbox, bool(sbox.setting._device.online), sbox._control.get_sensitive())
    return True


def _change_icon(allowed, icon):
    if allowed in _allowables_icons:
        icon._allowed = allowed
        icon.set_from_icon_name(_allowables_icons[allowed], Gtk.IconSize.LARGE_TOOLBAR)
        icon.set_tooltip_text(_allowables_tooltips[allowed])


def _create_sbox(s, device):
    sbox = Gtk.HBox(homogeneous=False, spacing=6)
    sbox.setting = s
    sbox.kind = s.kind
    if s.description:
        sbox.set_tooltip_text(s.description)
    lbl = Gtk.Label(s.label)
    lbl.set_alignment(0.0, 0.5)
    label = Gtk.EventBox()
    label.add(lbl)
    spinner = Gtk.Spinner()
    spinner.set_tooltip_text(_('Working') + '...')
    sbox._spinner = spinner
    failed = Gtk.Image.new_from_icon_name('dialog-warning', Gtk.IconSize.SMALL_TOOLBAR)
    failed.set_tooltip_text(_('Read/write operation failed.'))
    sbox._failed = failed
    change_icon = Gtk.Image.new_from_icon_name('changes-prevent', Gtk.IconSize.LARGE_TOOLBAR)
    sbox._change_icon = change_icon
    _change_icon(False, change_icon)
    change = Gtk.Button()
    change.set_relief(Gtk.ReliefStyle.NONE)
    change.add(change_icon)
    change.set_sensitive(True)
    change.connect('clicked', _change_click, sbox)

    if s.kind == _SETTING_KIND.toggle:
        control = ToggleControl(sbox)
    elif s.kind == _SETTING_KIND.range:
        control = SliderControl(sbox)
    elif s.kind == _SETTING_KIND.choice:
        control = _create_choice_control(sbox)
    elif s.kind == _SETTING_KIND.map_choice:
        control = MapChoiceControl(sbox)
    elif s.kind == _SETTING_KIND.multiple_toggle:
        control = MultipleToggleControl(sbox, change)
    elif s.kind == _SETTING_KIND.multiple_range:
        control = MultipleRangeControl(sbox, change)
    else:
        raise Exception('NotImplemented')
    control.set_sensitive(False)  # the first read will enable it
    control.layout(sbox, label, change, spinner, failed)
    sbox._control = control
    sbox.show_all()
    spinner.start()  # the first read will stop it
    failed.set_visible(False)
    return sbox


def _update_setting_item(sbox, value, is_online=True, sensitive=True):
    sbox._spinner.set_visible(False)
    sbox._spinner.stop()
    if value is None:
        sbox._control.set_sensitive(False)
        _change_icon(False, sbox._change_icon)
        sbox._failed.set_visible(is_online)
        return
    sbox._failed.set_visible(False)
    sbox._control.set_sensitive(False)
    sbox._control.set_value(value)
    sensitive = sbox._change_icon._allowed if sensitive is None else sensitive
    sbox._control.set_sensitive(sensitive is True)
    _change_icon(sensitive, sbox._change_icon)


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


def change_setting(device, setting, values):
    """External interface to change a setting and have the GUI show the change"""
    assert device == setting._device
    GLib.idle_add(_change_setting, device, setting, values, priority=99)


def _change_setting(device, setting, values):
    device_path = device.receiver.path if device.receiver else device.path
    if (device_path, device.number, setting.name) in _items:
        sbox = _items[(device_path, device.number, setting.name)]
    else:
        sbox = None
    _write_async(setting, values[-1], sbox, None, key=values[0] if len(values) > 1 else None)
