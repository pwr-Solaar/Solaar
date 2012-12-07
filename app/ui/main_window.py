#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from gi.repository import Gtk, Gdk, GObject

import ui
from logitech.unifying_receiver import status as _status
from . import config_panel as _config_panel


_RECEIVER_ICON_SIZE = Gtk.IconSize.LARGE_TOOLBAR
_DEVICE_ICON_SIZE = Gtk.IconSize.DIALOG
_STATUS_ICON_SIZE = Gtk.IconSize.LARGE_TOOLBAR
_PLACEHOLDER = '~'
_FALLBACK_ICON = 'preferences-desktop-peripherals'

#
#
#

def _make_receiver_box(name):
	frame = Gtk.Frame()
	frame._device = None
	frame.set_name(name)

	icon_set = ui.device_icon_set(name)
	icon = Gtk.Image.new_from_icon_set(icon_set, _RECEIVER_ICON_SIZE)
	icon.set_name('icon')
	icon.set_padding(2, 2)

	label = Gtk.Label('Scanning...')
	label.set_name('label')
	label.set_alignment(0, 0.5)

	pairing_icon = Gtk.Image.new_from_icon_name('network-wireless', _RECEIVER_ICON_SIZE)
	pairing_icon.set_name('pairing-icon')
	pairing_icon.set_tooltip_text('The pairing lock is open.')
	pairing_icon._tick = 0

	toolbar = Gtk.Toolbar()
	toolbar.set_name('toolbar')
	toolbar.set_style(Gtk.ToolbarStyle.ICONS)
	toolbar.set_icon_size(Gtk.IconSize.SMALL_TOOLBAR)
	toolbar.set_show_arrow(False)

	hbox = Gtk.HBox(homogeneous=False, spacing=8)
	hbox.pack_start(icon, False, False, 0)
	hbox.pack_start(label, True, True, 0)
	hbox.pack_start(pairing_icon, False, False, 0)
	hbox.pack_start(toolbar, False, False, 0)

	info_label = Gtk.Label()
	info_label.set_markup('<small>reading ...</small>')
	info_label.set_name('info-label')
	info_label.set_property('margin-left', 36)
	info_label.set_alignment(0, 0)
	info_label.set_selectable(True)

	def _update_info_label():
		device = frame._device
		if info_label.get_visible() and '\n' not in info_label.get_text():
			items = [('Path', device.path), ('Serial', device.serial)] + \
					[(f.kind, f.version) for f in device.firmware]
			info_label.set_markup('<small><tt>' + '\n'.join('%-13s: %s' % item for item in items) + '</tt></small>')

	def _toggle_info_label(action):
		active = action.get_active()
		for c in vbox.get_children()[1:]:
			c.set_visible(active)

		if active:
			GObject.timeout_add(50, _update_info_label)

	toggle_info_action = ui.action._toggle_action('info', 'Details', _toggle_info_label)
	toolbar.insert(toggle_info_action.create_tool_item(), 0)
	toolbar.insert(ui.action.pair(frame).create_tool_item(), -1)
	# toolbar.insert(ui.action.about.create_tool_item(), -1)

	vbox = Gtk.VBox(homogeneous=False, spacing=2)
	vbox.set_border_width(2)
	vbox.pack_start(hbox, True, True, 0)
	vbox.pack_start(Gtk.HSeparator(), False, False, 0)
	vbox.pack_start(info_label, True, True, 0)

	frame.add(vbox)
	frame.show_all()

	pairing_icon.set_visible(False)
	_toggle_info_label(toggle_info_action)
	return frame


def _make_device_box(index):
	frame = Gtk.Frame()
	frame._device = None
	frame.set_name(_PLACEHOLDER)

	icon = Gtk.Image.new_from_icon_name(_FALLBACK_ICON, _DEVICE_ICON_SIZE)
	icon.set_name('icon')
	icon.set_alignment(0.5, 0)

	label = Gtk.Label('Initializing...')
	label.set_name('label')
	label.set_alignment(0, 0.5)
	label.set_padding(4, 0)

	battery_icon = Gtk.Image.new_from_icon_name(ui.get_battery_icon(-1), _STATUS_ICON_SIZE)

	battery_label = Gtk.Label()
	battery_label.set_width_chars(6)
	battery_label.set_alignment(0, 0.5)

	light_icon = Gtk.Image.new_from_icon_name('light_unknown', _STATUS_ICON_SIZE)

	light_label = Gtk.Label()
	light_label.set_alignment(0, 0.5)
	light_label.set_width_chars(8)

	not_encrypted_icon = Gtk.Image.new_from_icon_name('security-low', _STATUS_ICON_SIZE - 1)
	not_encrypted_icon.set_name('not-encrypted')
	not_encrypted_icon.set_tooltip_text('The wireless link between this device and the Unifying Receiver is not encrypted.\n'
										'\n'
										'For pointing devices (mice, trackballs, trackpads), this is a minor security issue.\n'
										'\n'
										'It is, however, a major security issue for text-input devices (keyboards, numpads),\n'
										'because typed text can be sniffed inconspicuously by 3rd parties within range.')

	toolbar = Gtk.Toolbar()
	toolbar.set_name('toolbar')
	toolbar.set_style(Gtk.ToolbarStyle.ICONS)
	toolbar.set_icon_size(_STATUS_ICON_SIZE - 1)
	toolbar.set_show_arrow(False)

	status_box = Gtk.HBox(homogeneous=False, spacing=2)
	status_box.set_name('status')
	status_box.pack_start(battery_icon, False, True, 0)
	status_box.pack_start(battery_label, False, True, 0)
	status_box.pack_start(light_icon, False, True, 0)
	status_box.pack_start(light_label, False, True, 0)
	status_box.pack_end(toolbar, False, False, 0)
	status_box.pack_end(not_encrypted_icon, False, False, 0)

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
	info_label.set_name('info-label')
	info_label.set_property('margin-left', 54)
	info_label.set_selectable(True)
	info_label.set_alignment(0, 0)

	def _update_info_label():
		if info_label.get_text().count('\n') < 5:
			device = frame._device
			assert device

			items = []
			hid = device.protocol
			if hid:
				items += [('Protocol', 'HID++ %1.1f' % device.protocol)]
			else:
				items += [('Protocol', 'unknown')]
			items += [('Polling rate', '%d ms' % device.polling_rate), ('Wireless PID', device.wpid), ('Serial', device.serial)]
			firmware = device.firmware
			if firmware:
				items += [(f.kind, (f.name + ' ' + f.version).strip()) for f in firmware]

			info_label.set_markup('<small><tt>' + '\n'.join('%-13s: %s' % item for item in items) + '</tt></small>')

	def _toggle_info_label(action, frame):
		active = action.get_active()
		if active:
			# toggle_config_action.set_active(False)
			ui.find_children(frame, 'toolbar').get_children()[-1].set_active(False)

		vbox = frame.get_child()
		children = vbox.get_children()
		children[1].set_visible(active)  # separator
		children[2].set_visible(active)  # info label

		if active:
			GObject.timeout_add(30, _update_info_label)

	def _toggle_config(action, frame):
		active = action.get_active()
		if active:
			# toggle_info_action.set_active(False)
			ui.find_children(frame, 'toolbar').get_children()[0].set_active(False)

		vbox = frame.get_child()
		children = vbox.get_children()
		children[1].set_visible(active)  # separator
		children[3].set_visible(active)  # config box
		children[4].set_visible(active)  # unpair button

		if active:
			GObject.timeout_add(30, _config_panel.update, frame)

	toggle_info_action = ui.action._toggle_action('info', 'Details', _toggle_info_label, frame)
	toolbar.insert(toggle_info_action.create_tool_item(), 0)
	toggle_config_action = ui.action._toggle_action('preferences-system', 'Configuration', _toggle_config, frame)
	toolbar.insert(toggle_config_action.create_tool_item(), -1)

	vbox = Gtk.VBox(homogeneous=False, spacing=2)
	vbox.set_border_width(2)
	vbox.pack_start(device_box, True, True, 0)
	vbox.pack_start(Gtk.HSeparator(), False, False, 0)
	vbox.pack_start(info_label, False, False, 0)

	config_box = Gtk.VBox(homogeneous=False, spacing=4)
	config_box.set_name('config-box')
	config_box.set_property('margin', 8)
	vbox.pack_start(config_box, False, False, 0)

	unpair = Gtk.Button('Unpair')
	unpair.set_image(Gtk.Image.new_from_icon_name('edit-delete', Gtk.IconSize.BUTTON))
	unpair.connect('clicked', ui.action._unpair_device, frame)
	# unpair.set_property('margin-top', 12)
	unpair.set_property('margin-left', 104)
	unpair.set_property('margin-right', 104)
	vbox.pack_end(unpair, False, False, 0)

	vbox.show_all()
	frame.add(vbox)

	_toggle_info_label(toggle_info_action, frame)
	_toggle_config(toggle_config_action, frame)
	return frame


def toggle(window, trigger):
	if window.get_visible():
		position = window.get_position()
		window.hide()
		window.move(*position)
	else:
		if trigger and type(trigger) == Gtk.StatusIcon:
			x, y = window.get_position()
			if x == 0 and y == 0:
				x, y, _ = Gtk.StatusIcon.position_menu(Gtk.Menu(), trigger)
				window.move(x, y)
		window.present()
	return True


def _popup(window, trigger=None):
	if not window.get_visible():
		toggle(window, trigger)


def create(title, name, max_devices, systray=False):
	window = Gtk.Window()
	window.set_title(title)
	window.set_icon_name(ui.appicon(0))
	window.set_role('status-window')

	vbox = Gtk.VBox(homogeneous=False, spacing=12)
	vbox.set_border_width(4)

	rbox = _make_receiver_box(name)
	vbox.add(rbox)
	for i in range(1, 1 + max_devices):
		dbox = _make_device_box(i)
		vbox.add(dbox)
	vbox.set_visible(True)

	window.add(vbox)
	window._vbox = vbox

	geometry = Gdk.Geometry()
	geometry.min_width = 320
	geometry.min_height = 32
	window.set_geometry_hints(vbox, geometry, Gdk.WindowHints.MIN_SIZE)
	window.set_resizable(False)

	window.toggle_visible = lambda i: toggle(window, i)
	window.popup = lambda i=None: _popup(window, i)

	if systray:
		window.set_keep_above(True)
		# window.set_decorated(False)
		# window.set_type_hint(Gdk.WindowTypeHint.TOOLTIP)
		# window.set_skip_taskbar_hint(True)
		# window.set_skip_pager_hint(True)
		window.connect('delete-event', toggle)
	else:
		window.connect('delete-event', Gtk.main_quit)

	return window

#
#
#

def _update_receiver_box(frame, receiver):
	icon, label, pairing_icon, toolbar = ui.find_children(frame, 'icon', 'label', 'pairing-icon', 'toolbar')

	label.set_text(str(receiver.status))
	if receiver:
		frame._device = receiver
		icon.set_sensitive(True)
		if receiver.status.lock_open:
			if pairing_icon._tick == 0:
				def _pairing_tick(i, s):
					if s and s.lock_open:
						i.set_sensitive(bool(i._tick % 2))
						i._tick += 1
						return True
					i.set_visible(False)
					i.set_sensitive(True)
					i._tick = 0
				pairing_icon.set_visible(True)
				GObject.timeout_add(1000, _pairing_tick, pairing_icon, receiver.status)
		else:
			pairing_icon.set_visible(False)
			pairing_icon.set_sensitive(True)
			pairing_icon._tick = 0
		toolbar.set_sensitive(True)
	else:
		frame._device = None
		icon.set_sensitive(False)
		pairing_icon.set_visible(False)
		toolbar.set_sensitive(False)
		toolbar.get_children()[0].set_active(False)
		ui.find_children('info-label').set_text('')


def _update_device_box(frame, dev):
	if dev is None:
		frame.set_visible(False)
		frame.set_name(_PLACEHOLDER)
		frame._device = None
		_config_panel.update(frame)
		return

	icon, label, status_icons = ui.find_children(frame, 'icon', 'label', 'status')

	first_run = frame.get_name() != dev.name
	if first_run:
		frame._device = dev
		frame.set_name(dev.name)
		icon_set = ui.device_icon_set(dev.name, dev.kind)
		icon.set_from_icon_set(icon_set, _DEVICE_ICON_SIZE)
		label.set_markup('<b>' + dev.name + '</b>')
		toolbar = ui.find_children(frame, 'toolbar')
		for i in toolbar.get_children():
			i.set_active(False)

	battery_icon, battery_label, light_icon, light_label, not_encrypted_icon, _ = status_icons
	battery_level = dev.status.get(_status.BATTERY_LEVEL)

	if dev.status:
		label.set_sensitive(True)

		if battery_level is None:
			battery_icon.set_sensitive(False)
			battery_icon.set_from_icon_name(ui.get_battery_icon(-1), _STATUS_ICON_SIZE)
			battery_label.set_markup('<small>no status</small>')
			battery_label.set_sensitive(True)
		else:
			battery_icon.set_from_icon_name(ui.get_battery_icon(battery_level), _STATUS_ICON_SIZE)
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
			icon_name = 'light_%03d' % (20 * ((light_level + 50) // 100))
			light_icon.set_from_icon_name(icon_name, _STATUS_ICON_SIZE)
			light_icon.set_visible(True)
			light_label.set_text('%d lux' % light_level)
			light_label.set_visible(True)

		not_encrypted_icon.set_visible(dev.status.get(_status.ENCRYPTED) == False)

	else:
		label.set_sensitive(False)

		battery_icon.set_sensitive(False)
		battery_label.set_sensitive(False)
		if battery_level is None:
			battery_label.set_markup('<small>inactive</small>')
		else:
			battery_label.set_markup('%d%%' % battery_level)

		light_icon.set_visible(False)
		light_label.set_visible(False)
		not_encrypted_icon.set_visible(False)

	frame.set_visible(True)
	_config_panel.update(frame)


def update(window, receiver, device=None):
	assert receiver is not None
	# print ("update %s %s, %s" % (receiver, receiver.status, device))
	window.set_icon_name(ui.appicon(receiver.status))

	vbox = window._vbox
	frames = list(vbox.get_children())
	assert len(frames) == 1 + receiver.max_devices, frames

	if device:
		_update_device_box(frames[device.number], None if device.status is None else device)
	else:
		_update_receiver_box(frames[0], receiver)
		if not receiver:
			for frame in frames[1:]:
				_update_device_box(frame, None)
