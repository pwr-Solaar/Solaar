#
#
#

from gi.repository import (Gtk, Gdk)

import ui
from logitech.devices.constants import (STATUS, PROPS)


_SMALL_DEVICE_ICON_SIZE = Gtk.IconSize.BUTTON
_DEVICE_ICON_SIZE = Gtk.IconSize.DIALOG
_STATUS_ICON_SIZE = Gtk.IconSize.DND
_PLACEHOLDER = '~'


def _update_receiver_box(box, receiver):
	button, label, frame, info = ui.find_children(box,
					'info-button', 'status-label', 'info-frame', 'info-label')
	label.set_text(receiver.status_text or '')
	if receiver.status < STATUS.CONNECTED:
		button.set_sensitive(False)
		button.set_active(False)
		frame.set_visible(False)
		info.set_text('')
	else:
		button.set_sensitive(True)
		if not info.get_text():
			info.set_text('Serial:\t\t%s\nFirmware:   \t%s\nBootloader: \t%s\nMax devices:\t%s' %
							(receiver.serial, receiver.firmware[0], receiver.firmware[1], receiver.max_devices))

def _update_device_box(frame, dev):
	if dev is None:
		frame.set_visible(False)
		frame.set_name(_PLACEHOLDER)
		return

	icon, label = ui.find_children(frame, 'icon', 'label')

	frame.set_visible(True)
	if frame.get_name() != dev.name:
		frame.set_name(dev.name)
		icon.set_from_icon_name(ui.get_icon(dev.name, dev.kind), _DEVICE_ICON_SIZE)
		icon.set_tooltip_text(dev.name)
		label.set_markup('<b>' + dev.name + '</b>')

	status = ui.find_children(frame, 'status')
	if dev.status < STATUS.CONNECTED:
		icon.set_sensitive(False)
		icon.set_tooltip_text(dev.status_text)
		label.set_sensitive(False)
		status.set_visible(False)
		return

	icon.set_sensitive(True)
	icon.set_tooltip_text('')
	label.set_sensitive(True)
	status.set_visible(True)
	status_icons = status.get_children()

	battery_icon, battery_label = status_icons[0:2]
	battery_level = dev.props.get(PROPS.BATTERY_LEVEL)
	if battery_level is None:
		battery_icon.set_sensitive(False)
		battery_icon.set_from_icon_name('battery_unknown', _STATUS_ICON_SIZE)
		battery_label.set_sensitive(False)
		battery_label.set_text('')
	else:
		battery_icon.set_sensitive(True)
		icon_name = 'battery_%03d' % (20 * ((battery_level + 10) // 20))
		battery_icon.set_from_icon_name(icon_name, _STATUS_ICON_SIZE)
		battery_label.set_sensitive(True)
		battery_label.set_text('%d%%' % battery_level)

	battery_status = dev.props.get(PROPS.BATTERY_STATUS)
	if battery_status is None:
		battery_icon.set_tooltip_text('')
	else:
		battery_icon.set_tooltip_text(battery_status)

	light_icon, light_label = status_icons[2:4]
	light_level = dev.props.get(PROPS.LIGHT_LEVEL)
	if light_level is None:
		light_icon.set_visible(False)
		light_label.set_visible(False)
	else:
		light_icon.set_visible(True)
		icon_name = 'light_%03d' % (20 * ((light_level + 50) // 100))
		light_icon.set_from_icon_name(icon_name, _STATUS_ICON_SIZE)
		light_label.set_visible(True)
		light_label.set_text('%d lux' % light_level)


def update(window, receiver):
	if window and window.get_child():
		window.set_icon_name(ui.appicon(receiver.status))

		vbox = window.get_child()
		controls = list(vbox.get_children())

		_update_receiver_box(controls[0], receiver)

		for index in range(1, len(controls)):
			dev = receiver.devices[index] if index in receiver.devices else None
			_update_device_box(controls[index], dev)

#
#
#

def _receiver_box(name):
	info_button = Gtk.ToggleButton()
	info_button.set_name('info-button')
	info_button.set_alignment(0.5, 0)
	info_button.set_image(Gtk.Image.new_from_icon_name(name, _SMALL_DEVICE_ICON_SIZE))
	info_button.set_relief(Gtk.ReliefStyle.NONE)
	info_button.set_tooltip_text(name)
	info_button.set_sensitive(False)

	label = Gtk.Label('Initializing...')
	label.set_name('status-label')
	label.set_alignment(0, 0.5)

	toolbar = Gtk.Toolbar()
	toolbar.set_name('buttons')
	toolbar.set_style(Gtk.ToolbarStyle.ICONS)
	toolbar.set_icon_size(Gtk.IconSize.MENU)
	toolbar.set_show_arrow(False)
	toolbar.insert(ui.action.pair.create_tool_item(), 0)

	info_label = Gtk.Label('')
	info_label.set_name('info-label')
	info_label.set_alignment(0, 0.5)
	info_label.set_padding(24, 4)
	info_label.set_selectable(True)

	info_frame = Gtk.Frame()
	info_frame.set_name('info-frame')
	info_frame.set_label(name)
	info_frame.add(info_label)

	info_button.connect('toggled', lambda b: info_frame.set_visible(b.get_active()))

	hbox = Gtk.HBox(homogeneous=False, spacing=8)
	hbox.pack_start(info_button, False, False, 0)
	hbox.pack_start(label, True, True, 0)
	hbox.pack_end(toolbar, False, False, 0)

	vbox = Gtk.VBox(homogeneous=False, spacing=4)
	vbox.set_border_width(4)
	vbox.pack_start(hbox, True, True, 0)
	vbox.pack_start(info_frame, True, True, 0)
	vbox.show_all()

	info_frame.set_visible(False)
	return vbox


def _device_box(has_status_icons=True, has_frame=True):
	box = Gtk.HBox(homogeneous=False, spacing=10)
	box.set_border_width(4)

	icon = Gtk.Image()
	icon.set_name('icon')
	icon.set_from_icon_name('image-missing', _DEVICE_ICON_SIZE)
	icon.set_alignment(0.5, 0)
	box.pack_start(icon, False, False, 0)

	vbox = Gtk.VBox(homogeneous=False, spacing=8)
	box.pack_start(vbox, True, True, 0)

	label = Gtk.Label('Initializing...')
	label.set_name('label')
	label.set_alignment(0, 0.5)

	status_box = Gtk.HBox(homogeneous=False, spacing=0)
	status_box.set_name('status')

	if has_status_icons:
		vbox.pack_start(label, True, True, 0)

		battery_icon = Gtk.Image.new_from_icon_name('battery_unknown', _STATUS_ICON_SIZE)
		status_box.pack_start(battery_icon, False, True, 0)

		battery_label = Gtk.Label()
		battery_label.set_width_chars(6)
		battery_label.set_alignment(0, 0.5)
		status_box.pack_start(battery_label, False, True, 0)

		light_icon = Gtk.Image.new_from_icon_name('light_unknown', _STATUS_ICON_SIZE)
		status_box.pack_start(light_icon, False, True, 0)

		light_label = Gtk.Label()
		light_label.set_alignment(0, 0.5)
		light_label.set_width_chars(8)
		status_box.pack_start(light_label, False, True, 0)
	else:
		status_box.pack_start(label, True, True, 0)

	vbox.pack_start(status_box, True, True, 0)

	box.show_all()

	if has_frame:
		frame = Gtk.Frame()
		frame.add(box)
		return frame
	else:
		return box


def toggle(window, trigger):
	# print 'window toggle', window, trigger
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


def create(title, name, max_devices, systray=False):
	window = Gtk.Window()
	window.set_title(title)
	window.set_icon_name(ui.appicon(0))
	window.set_role('status-window')

	vbox = Gtk.VBox(homogeneous=False, spacing=4)
	vbox.set_border_width(4)

	rbox = _receiver_box(name)
	vbox.add(rbox)
	for i in range(1, 1 + max_devices):
		dbox = _device_box()
		vbox.add(dbox)
	vbox.set_visible(True)

	window.add(vbox)

	geometry = Gdk.Geometry()
	geometry.min_width = 300
	geometry.min_height = 40
	window.set_geometry_hints(vbox, geometry, Gdk.WindowHints.MIN_SIZE)
	window.set_resizable(False)

	window.toggle_visible = lambda i: toggle(window, i)

	if systray:
		window.set_keep_above(True)
		window.connect('delete-event', toggle)
	else:
		window.connect('delete-event', Gtk.main_quit)

	return window
