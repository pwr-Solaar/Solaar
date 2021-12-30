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
    if sbox:
        failed, spinner, control = _get_failed_spinner_control(sbox)
        control.set_sensitive(False)
        failed.set_visible(False)
        spinner.set_visible(True)
        spinner.start()

    def _do_write(s, v, sb, key):
        if key is None:
            v = setting.write(v)
        else:
            v = setting.write_key_value(key, v)
            v = {key: v}
        if sb:
            GLib.idle_add(_update_setting_item, sb, v, True, sensitive, priority=99)

    _ui_async(_do_write, setting, value, sbox, key)


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


#
#
#


class ToggleControl(Gtk.Switch):
    def __init__(self, setting, delegate=None):
        super().__init__(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.setting = setting
        self.delegate = delegate
        self.connect('notify::active', self.changed)

    def set_value(self, value):
        self.set_state(value)

    def changed(self, *args):
        if self.get_sensitive():
            self.delegate.update() if self.delegate else self.update()

    def update(self):
        _write_async(self.setting, self.get_active() is True, self.get_parent())


class SliderControl(Gtk.Scale):
    def __init__(self, setting, delegate=None):
        super().__init__(halign=Gtk.Align.FILL)
        self.setting = setting
        self.delegate = delegate
        self.timer = None
        self.set_range(*self.setting.range)
        self.set_round_digits(0)
        self.set_digits(0)
        self.set_increments(1, 5)
        self.connect('value-changed', self.changed)

    def changed(self, *args):
        if self.get_sensitive():
            if self.timer:
                self.timer.cancel()
            self.timer = _Timer(0.5, lambda: GLib.idle_add(self.do_change))
            self.timer.start()

    def do_change(self):
        self.timer.cancel()
        self.delegate.update() if self.delegate else self.update()

    def update(self):
        _write_async(self.setting, int(self.get_value()), self.get_parent())


def _create_choice_control(setting, delegate=None, choices=None):
    if 50 > len(choices if choices else setting.choices):
        return ChoiceControlLittle(setting, choices=choices, delegate=delegate)
    else:
        return ChoiceControlBig(setting, choices=choices, delegate=delegate)


class ChoiceControlLittle(Gtk.ComboBoxText):
    def __init__(self, setting, delegate=None, choices=None):
        super().__init__(halign=Gtk.Align.FILL)
        self.setting = setting
        self.delegate = delegate
        self.choices = choices if choices is not None else setting.choices
        for entry in self.choices:
            self.append(str(int(entry)), str(entry))
        self.connect('changed', self.changed)

    def get_value(self):
        id = int(self.get_active_id())
        return next((x for x in self.choices if x == id), None)

    def set_value(self, value):
        self.set_active_id(str(int(value)))

    def set_choices(self, choices):
        self.remove_all()
        for choice in choices:
            self.append(str(int(choice)), _(str(choice)))

    def changed(self, *args):
        if self.get_sensitive():
            self.delegate.update() if self.delegate else self.update()

    def update(self):
        _write_async(self.setting, self.get_active_id(), self.get_parent())


class ChoiceControlBig(Gtk.Entry):
    def __init__(self, setting, delegate=None, choices=None):
        super().__init__(halign=Gtk.Align.FILL)
        self.setting = setting
        self.delegate = delegate
        self.choices = choices if choices is not None else setting.choices
        self.value = None
        width = max([len(str(x)) for x in self.choices]) + 2  # maximum choice length plus space for icon
        self.set_width_chars(width)
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
        key = self.get_text()
        return next((x for x in self.choices if x == key), None)

    def set_value(self, value):
        self.set_text(str(next((x for x in self.choices if x == value), None)))

    def changed(self, *args):
        self.value = next((x for x in self.choices if x == self.get_text()), None)
        icon = 'dialog-warning' if self.value is None else 'dialog-question' if self.get_sensitive() else ''
        self.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)
        tooltip = _('Incomplete') if self.value is None else _('Complete - ENTER to change')
        self.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, tooltip)

    def activate(self, *args):
        if self.value is not None and self.get_sensitive():
            self.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, '')
            self.delegate.update() if self.delegate else self.update()

    def select(self, completion, model, iter):
        self.set_value(model.get(iter, 0)[0])
        if self.value and self.get_sensitive():
            self.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, '')
            self.delegate.update() if self.delegate else self.update()

    def update(self):
        _write_async(self.setting, int(self.value), self.get_parent())


class MapChoiceControl(Gtk.HBox):
    def __init__(self, setting):
        super().__init__(homogeneous=False, spacing=6)
        self.setting = setting
        self.keyBox = Gtk.ComboBoxText()
        for entry in setting.choices:
            self.keyBox.append(str(int(entry)), _(str(entry)))
        self.keyBox.set_active(0)
        key_choice = int(self.keyBox.get_active_id())
        self.value_choices = self.setting.choices[key_choice]
        self.valueBox = _create_choice_control(setting, choices=self.value_choices, delegate=self)
        self.pack_start(self.keyBox, False, False, 0)
        self.pack_end(self.valueBox, False, False, 0)
        self.keyBox.connect('changed', self.map_value_notify_key)

    def set_value(self, value):
        self.valueBox.set_sensitive(self.get_sensitive())
        if value.get(self.keyBox.get_active_id()) is not None:
            self.valueBox.set_value(value.get(self.keyBox.get_active_id()))
        self.valueBox.set_sensitive(True)

    def map_populate_value_box(self, key_choice):
        choices = self.setting.choices[int(key_choice)]
        if choices != self.value_choices:
            self.value_choices = choices
            self.valueBox.remove_all()
            self.valueBox.set_choices(choices)
        current = self.setting._value.get(str(key_choice)) if self.setting._value else None
        if current is not None:
            self.valueBox.set_value(current)

    def map_value_notify_key(self, *args):
        key_choice = self.keyBox.get_active_id()
        if self.keyBox.get_sensitive():
            self.map_populate_value_box(key_choice)

    def update(self):
        key_choice = self.keyBox.get_active_id()
        if key_choice is not None and self.valueBox.get_sensitive() and self.valueBox.get_value() is not None:
            if self.setting._value.get(key_choice) != int(self.valueBox.get_value()):
                self.setting._value[key_choice] = int(self.valueBox.get_value())
                _write_async_key_value(self.setting, key_choice, self.setting._value[key_choice], self.get_parent())


def _create_multiple_toggle_control(setting, change):
    def _toggle_notify(control, _, setting):
        if control.get_sensitive():
            key = control._setting_key
            new_state = control.get_active()
            if setting._value[key] != new_state:
                setting._value[key] = new_state
                p = control
                for _ in range(5):  # go up widget chain
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
            _write_async_key_value(setting, str(int(item)), setting._value[str(int(item))], p)

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

_allowables_icons = {True: 'changes-allow', False: 'changes-prevent', _SENSITIVITY_IGNORE: 'dialog-error'}
_allowables_tooltips = {
    True: _('Changes allowed'),
    False: _('No changes allowed'),
    _SENSITIVITY_IGNORE: _('Ignore this setting')
}
_next_allowable = {True: False, False: _SENSITIVITY_IGNORE, _SENSITIVITY_IGNORE: True}
_icons_allowables = {v: k for k, v in _allowables_icons.items()}


# clicking on the lock icon changes from changeable to unchangeable to ignore
def _change_click(button, arg):
    control, sbox, device, name = arg
    icon = button.get_children()[0]
    icon_name, _ = icon.get_icon_name()
    allowed = _icons_allowables.get(icon_name, True)
    new_allowed = _next_allowable[allowed]
    control.set_sensitive(new_allowed is True)
    _change_icon(new_allowed, icon)
    if device.persister:  # remember the new setting sensitivity
        device.persister.set_sensitivity(name, new_allowed)
    if allowed == _SENSITIVITY_IGNORE:  # update setting if it was being ignored
        setting = next((s for s in device.settings if s.name == name), None)
        if setting:
            persisted = device.persister.get(setting.name) if device.persister else None
            if persisted is not None:
                _write_async(setting, persisted, sbox)
            else:
                _read_async(setting, True, sbox, bool(device.online), control.get_sensitive())
    return True


def _change_icon(allowed, icon):
    if allowed in _allowables_icons:
        icon._allowed = allowed
        icon.set_from_icon_name(_allowables_icons[allowed], Gtk.IconSize.LARGE_TOOLBAR)
        icon.set_tooltip_text(_allowables_tooltips[allowed])


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
    change = Gtk.Button()
    change.set_relief(Gtk.ReliefStyle.NONE)
    change.add(change_icon)

    if s.kind == _SETTING_KIND.toggle:
        control = ToggleControl(s)
    elif s.kind == _SETTING_KIND.range:
        control = SliderControl(s)
    elif s.kind == _SETTING_KIND.choice:
        control = _create_choice_control(s)
    elif s.kind == _SETTING_KIND.map_choice:
        control = MapChoiceControl(s)
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
    change.connect('clicked', _change_click, (control, sbox, device, s.name))

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
    if isinstance(control, ToggleControl) or isinstance(control, SliderControl):
        control.set_value(value)
    elif isinstance(control, ChoiceControlBig) or isinstance(control, ChoiceControlLittle):
        control.set_value(value)
    elif isinstance(control, MapChoiceControl):
        control.set_value(value)
    elif isinstance(control, Gtk.HBox):
        control.set_value(value)
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

    sensitive = sbox._change_icon._allowed if sensitive is None else sensitive
    control.set_sensitive(sensitive is True)
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


def change_setting(device, setting, values):
    device = setting._device
    device_path = device.receiver.path if device.receiver else device.path
    if (device_path, device.number, setting.name) in _items:
        sbox = _items[(device_path, device.number, setting.name)]
    else:
        sbox = None
    _write_async(setting, values[-1], sbox, None, key=values[0] if len(values) > 1 else None)
