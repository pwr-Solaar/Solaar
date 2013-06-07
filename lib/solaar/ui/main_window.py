#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger(__name__)
del getLogger

from gi.repository import Gtk, Gdk, GLib

from solaar import NAME
from logitech.unifying_receiver import status as _status, hidpp10 as _hidpp10
from . import config_panel as _config_panel
from . import action as _action, icons as _icons

#
#
#

_RECEIVER_ICON_SIZE = Gtk.IconSize.LARGE_TOOLBAR
_DEVICE_ICON_SIZE = Gtk.IconSize.DIALOG
_STATUS_ICON_SIZE = Gtk.IconSize.LARGE_TOOLBAR
_TOOLBAR_ICON_SIZE = Gtk.IconSize.MENU
_PLACEHOLDER = '~'
_FALLBACK_ICON = 'preferences-desktop-peripherals'
_MAX_DEVICES = 7

#
#
#

def _make_receiver_box(receiver):
	frame = Gtk.Frame()
	# frame.set_shadow_type(Gtk.ShadowType.NONE)
	frame._device = receiver

	icon_set = _icons.device_icon_set(receiver.name)
	icon = Gtk.Image.new_from_icon_set(icon_set, _RECEIVER_ICON_SIZE)
	icon.set_padding(2, 2)
	frame._icon = icon

	label = Gtk.Label('Scanning...')
	label.set_alignment(0, 0.5)
	frame._label = label

	pairing_icon = Gtk.Image.new_from_icon_name('network-wireless', _TOOLBAR_ICON_SIZE)
	pairing_icon.set_tooltip_text('The pairing lock is open.')
	pairing_icon._tick = 0
	frame._pairing_icon = pairing_icon

	toolbar = Gtk.Toolbar()
	toolbar.set_style(Gtk.ToolbarStyle.ICONS)
	toolbar.set_icon_size(_TOOLBAR_ICON_SIZE)
	toolbar.set_show_arrow(False)
	frame._toolbar = toolbar

	hbox = Gtk.HBox(homogeneous=False, spacing=8)
	hbox.pack_start(icon, False, False, 0)
	hbox.pack_start(label, True, True, 0)
	hbox.pack_start(pairing_icon, False, False, 0)
	hbox.pack_start(toolbar, False, False, 0)

	info_label = Gtk.Label()
	info_label.set_markup('<small>reading ...</small>')
	info_label.set_sensitive(False)
	info_label.set_property('margin-left', 36)
	info_label.set_alignment(0, 0)
	info_label.set_selectable(True)
	frame._info_label = info_label

	def _update_info_label(f):
		device = f._device
		if True:  # f._info_label.get_visible() and '\n' not in f._info_label.get_text():
			items = [('Path', device.path), ('Serial', device.serial)] + \
					list((fw.kind, fw.version) for fw in device.firmware) + \
					[None]

			notification_flags = _hidpp10.get_notification_flags(device)
			if notification_flags:
				notification_flags = _hidpp10.NOTIFICATION_FLAG.flag_names(notification_flags)
			else:
				notification_flags = ('(none)',)
			items[-1] = ('Notifications', ('\n%16s' % ' ').join(notification_flags))

			f._info_label.set_markup('<small><tt>%s</tt></small>' % '\n'.join('%-14s: %s' % i for i in items if i))
		f._info_label.set_sensitive(True)

	def _toggle_info_label(action, f):
		active = action.get_active()
		vb = f.get_child()
		for c in vb.get_children()[1:]:
			c.set_visible(active)

		if active:
			GLib.timeout_add(20, _update_info_label, f)

	toggle_info_action = _action.make_toggle('dialog-information', 'Details', _toggle_info_label, frame)
	toolbar.insert(toggle_info_action.create_tool_item(), 0)
	pair_action = _action.pair(frame)
	if not receiver.unifying_supported:
		pair_action.set_sensitive(False)
		pair_action.set_tooltip('Pairing not supported by this receiver')
	toolbar.insert(pair_action.create_tool_item(), -1)

	vbox = Gtk.VBox(homogeneous=False, spacing=2)
	vbox.set_border_width(2)
	vbox.pack_start(hbox, True, True, 0)
	vbox.pack_start(Gtk.HSeparator(), False, False, 0)
	vbox.pack_start(info_label, True, True, 0)

	frame.add(vbox)
	frame.show_all()

	pairing_icon.set_visible(False)
	_toggle_info_label(toggle_info_action, frame)
	return frame


def _make_device_box(index):
	frame = Gtk.Frame()
	frame._device = None
	frame.set_name(_PLACEHOLDER)

	icon = Gtk.Image.new_from_icon_name(_FALLBACK_ICON, _DEVICE_ICON_SIZE)
	icon.set_alignment(0.5, 0)
	icon.set_padding(2, 2)
	frame._icon = icon

	label = Gtk.Label('Initializing...')
	label.set_alignment(0, 0.5)
	label.set_padding(4, 0)
	frame._label = label

	battery_icon = Gtk.Image.new_from_icon_name(_icons.battery(), _STATUS_ICON_SIZE)

	battery_label = Gtk.Label()
	battery_label.set_width_chars(8)
	battery_label.set_alignment(0, 0.5)

	light_icon = Gtk.Image.new_from_icon_name(_icons.lux(), _STATUS_ICON_SIZE)

	light_label = Gtk.Label()
	light_label.set_alignment(0, 0.5)
	light_label.set_width_chars(8)

	not_encrypted_icon = Gtk.Image.new_from_icon_name('security-low', _STATUS_ICON_SIZE)
	not_encrypted_icon.set_name('not-encrypted')
	not_encrypted_icon.set_tooltip_text('The wireless link between this device and its receiver is not encrypted.\n'
										'\n'
										'For pointing devices (mice, trackballs, trackpads), this is a minor security issue.\n'
										'\n'
										'It is, however, a major security issue for text-input devices (keyboards, numpads),\n'
										'because typed text can be sniffed inconspicuously by 3rd parties within range.')

	toolbar = Gtk.Toolbar()
	toolbar.set_style(Gtk.ToolbarStyle.ICONS)
	toolbar.set_icon_size(_TOOLBAR_ICON_SIZE)
	toolbar.set_show_arrow(False)
	frame._toolbar = toolbar

	status_box = Gtk.HBox(homogeneous=False, spacing=2)
	status_box.pack_start(battery_icon, False, True, 0)
	status_box.pack_start(battery_label, False, True, 0)
	status_box.pack_start(light_icon, False, True, 0)
	status_box.pack_start(light_label, False, True, 0)
	status_box.pack_end(toolbar, False, False, 0)
	status_box.pack_end(not_encrypted_icon, False, False, 0)
	frame._status_icons = status_box

	status_vbox = Gtk.VBox(homogeneous=False, spacing=4)
	status_vbox.pack_start(label, True, True, 0)
	status_vbox.pack_start(status_box, True, True, 0)

	device_box = Gtk.HBox(homogeneous=False, spacing=4)
	# device_box.set_border_width(4)
	device_box.pack_start(icon, False, False, 0)
	device_box.pack_start(status_vbox, True, True, 0)
	device_box.show_all()

	info_label = Gtk.Label()
	info_label.set_markup('<small>reading ...</small>')
	info_label.set_property('margin-left', 54)
	info_label.set_sensitive(False)
	info_label.set_selectable(True)
	info_label.set_alignment(0, 0)
	frame._info_label = info_label

	def _update_info_label(f):
		if True:  # frame._info_label.get_text().count('\n') < 4:
			device = f._device
			assert device

			hid = device.protocol
			items = [
					('Protocol', 'HID++ %1.1f' % hid if hid else 'unknown'),
					('Polling rate', '%d ms' % device.polling_rate) if device.polling_rate else None,
					('Wireless PID', device.wpid),
					('Serial', device.serial) ] + \
					list((fw.kind, (fw.name + ' ' + fw.version).strip()) for fw in device.firmware) + \
					[None]

			if device.status:
				notification_flags = _hidpp10.get_notification_flags(device)
				if notification_flags:
					notification_flags = _hidpp10.NOTIFICATION_FLAG.flag_names(notification_flags)
				else:
					notification_flags = ('(none)',)
				items[-1] = ('Notifications', ('\n%16s' % ' ').join(notification_flags))

			frame._info_label.set_markup('<small><tt>%s</tt></small>' % '\n'.join('%-14s: %s' % i for i in items if i))
		frame._info_label.set_sensitive(True)

	def _toggle_info_label(action, f):
		active = action.get_active()
		if active:
			# set config toggle button as inactive
			f._toolbar.get_children()[-1].set_active(False)

		vb = f.get_child()
		children = vb.get_children()
		children[1].set_visible(active)  # separator
		children[2].set_visible(active)  # info label

		if active:
			GLib.timeout_add(30, _update_info_label, f)

	def _toggle_config(action, f):
		active = action.get_active()
		if active:
			# set info toggle button as inactive
			f._toolbar.get_children()[0].set_active(False)

		vb = f.get_child()
		children = vb.get_children()
		children[1].set_visible(active)  # separator
		children[3].set_visible(active)  # config box
		children[4].set_visible(active)  # unpair button

		if active:
			GLib.timeout_add(30, _config_panel.update, f)

	toggle_info_action = _action.make_toggle('dialog-information', 'Details', _toggle_info_label, frame)
	toolbar.insert(toggle_info_action.create_tool_item(), 0)
	toggle_config_action = _action.make_toggle('preferences-system', 'Configuration', _toggle_config, frame)
	toolbar.insert(toggle_config_action.create_tool_item(), -1)

	vbox = Gtk.VBox(homogeneous=False, spacing=2)
	vbox.set_border_width(2)
	vbox.pack_start(device_box, True, True, 0)
	vbox.pack_start(Gtk.HSeparator(), False, False, 0)
	vbox.pack_start(info_label, False, False, 0)

	frame._config_box = _config_panel.create()
	vbox.pack_start(frame._config_box, False, False, 0)

	unpair = Gtk.Button('Unpair')
	unpair.set_image(Gtk.Image.new_from_icon_name('edit-delete', Gtk.IconSize.BUTTON))
	unpair.connect('clicked', _action._unpair_device, frame)
	unpair.set_relief(Gtk.ReliefStyle.NONE)
	unpair.set_property('margin-left', 106)
	unpair.set_property('margin-right', 106)
	unpair.set_property('can-focus', False)  # exclude from tab-navigation
	vbox.pack_end(unpair, False, False, 0)

	vbox.show_all()
	frame.add(vbox)

	_toggle_info_label(toggle_info_action, frame)
	_toggle_config(toggle_config_action, frame)
	return frame


def _hide(w, _=None):
	position = w.get_position()
	w.hide()
	w.move(*position)
	return True


def _show(w, trigger=None):
	if w.get_visible() or w._was_shown:
		w.present()
	else:
		w._was_shown = True
		# if _log.isEnabledFor(_DEBUG):
		# 	_log.debug("first show %s", trigger)
		if isinstance(trigger, Gtk.StatusIcon):
			x, y, _ = Gtk.StatusIcon.position_menu(trigger._menu, trigger)
			w.present()
			w.move(x, y)
		else:
			w.set_position(Gtk.WindowPosition.CENTER)
			w.present()

	return True


# all created windows will be placed here, keyed by the receiver path
_windows = {}


def _create(receiver):
	window = Gtk.Window()

	window.set_title(NAME + ': ' + receiver.name)
	window.set_role('status-window')
	window.set_type_hint(Gdk.WindowTypeHint.UTILITY)

	vbox = Gtk.VBox(homogeneous=False, spacing=12)
	vbox.set_border_width(4)

	rbox = _make_receiver_box(receiver)
	vbox.add(rbox)
	for i in range(1, _MAX_DEVICES):
		dbox = _make_device_box(i)
		vbox.add(dbox)
	vbox.set_visible(True)

	window.add(vbox)

	geometry = Gdk.Geometry()
	geometry.min_width = 360
	geometry.min_height = 32
	window.set_geometry_hints(vbox, geometry, Gdk.WindowHints.MIN_SIZE)

	window.set_resizable(False)
	window.set_skip_taskbar_hint(True)
	window.set_skip_pager_hint(True)
	window.set_keep_above(True)
	# window.set_position(Gtk.WindowPosition.MOUSE)
	# window.set_decorations(Gdk.DECOR_BORDER | Gdk.DECOR_TITLE)
	window.connect('delete-event', _hide)
	window._was_shown = False

	_windows[receiver.path] = window
	return window


def _destroy(receiver):
	w = _windows.pop(receiver.path, None)
	if w:
		w.destroy()


def popup(trigger_widget, receiver_path, status_icon=None):
	if receiver_path is not None:
		w = _windows.get(receiver_path)
		if w:
			_show(w, status_icon)
			return

	toggle_all(status_icon)


def toggle_all(status_icon):
	if not _windows:
		return

	visible = (w.get_visible() for w in _windows.values())
	if all(visible):
		for w in _windows.values():
			_hide(w)
	else:
		for w in _windows.values():
			_show(w, status_icon)

#
#
#

def _update_receiver_box(frame, receiver):
	assert frame
	assert receiver

	frame._label.set_text(str(receiver.status))
	if receiver.status.lock_open:
		if frame._pairing_icon._tick == 0:
			def _pairing_tick(i, s):
				if s and s.lock_open:
					i.set_sensitive(bool(i._tick % 2))
					i._tick += 1
					return True
				i.set_visible(False)
				i.set_sensitive(True)
				i._tick = 0
			frame._pairing_icon.set_visible(True)
			GLib.timeout_add(1000, _pairing_tick, frame._pairing_icon, receiver.status)
	else:
		frame._pairing_icon.set_visible(False)
		frame._pairing_icon.set_sensitive(True)
		frame._pairing_icon._tick = 0


def _update_device_box(frame, dev):
	if dev is None:
		frame.set_visible(False)
		frame.set_name(_PLACEHOLDER)
		frame._device = None
		_config_panel.update(frame)
		return

	first_run = frame.get_name() != dev.name
	if first_run:
		frame._device = dev
		frame.set_name(dev.name)
		icon_set = _icons.device_icon_set(dev.name, dev.kind)
		frame._icon.set_from_icon_set(icon_set, _DEVICE_ICON_SIZE)
		frame._label.set_markup('<b>%s</b>' % dev.name)
		for i in frame._toolbar.get_children():
			i.set_active(False)

		if not dev.receiver.unifying_supported:
			unpair_button = frame.get_child().get_children()[-1]
			unpair_button.set_sensitive(False)
			unpair_button.set_tooltip_text('Unpairing not supported by this device')

	battery_icon, battery_label, light_icon, light_label, not_encrypted_icon, _ = frame._status_icons
	battery_level = dev.status.get(_status.BATTERY_LEVEL)

	if dev.status:
		frame._label.set_sensitive(True)

		if battery_level is None:
			battery_icon.set_sensitive(False)
			battery_icon.set_from_icon_name(_icons.battery(), _STATUS_ICON_SIZE)
			battery_label.set_markup('<small>no status</small>')
			battery_label.set_sensitive(True)
		else:
			battery_charging = dev.status.get(_status.BATTERY_CHARGING)
			icon_name = _icons.battery(battery_level, battery_charging)
			battery_icon.set_from_icon_name(icon_name, _STATUS_ICON_SIZE)
			battery_icon.set_sensitive(True)
			battery_label.set_text('%d%%' % battery_level)
			battery_label.set_sensitive(True)

		battery_status = dev.status.get(_status.BATTERY_STATUS)
		battery_icon.set_tooltip_text(battery_status or '')

		light_level = dev.status.get(_status.LIGHT_LEVEL)
		if light_level is None:
			light_icon.set_visible(False)
			light_label.set_visible(False)
		else:
			icon_name = _icons.lux(light_level)
			light_icon.set_from_icon_name(icon_name, _STATUS_ICON_SIZE)
			light_icon.set_visible(True)
			light_label.set_text('%d lux' % light_level)
			light_label.set_visible(True)

		not_encrypted_icon.set_visible(dev.status.get(_status.ENCRYPTED) == False)

	else:
		frame._label.set_sensitive(False)

		battery_icon.set_sensitive(False)
		battery_label.set_sensitive(False)
		if battery_level is None:
			battery_label.set_markup('<small>inactive</small>')
		else:
			battery_label.set_markup('%d%%' % battery_level)

		light_icon.set_visible(False)
		light_label.set_visible(False)
		not_encrypted_icon.set_visible(False)

		frame._toolbar.get_children()[-1].set_active(False)

	frame.set_visible(True)
	_config_panel.update(frame)


def update(device, need_popup=False, status_icon=None):
	assert device is not None
	# print ("main_window.update", device)

	receiver = device if device.kind is None else device.receiver
	assert receiver is not None, '%s has no receiver' % device
	w = _windows.get(receiver.path)
	if receiver and not w:
		w = _create(receiver)

	if w:
		if receiver:
			if need_popup:
				_show(w, status_icon)
			vbox = w.get_child()
			frames = list(vbox.get_children())

			if device is receiver:
				_update_receiver_box(frames[0], receiver)
			else:
				_update_device_box(frames[device.number], None if device.status is None else device)
		else:
			_destroy(receiver)
