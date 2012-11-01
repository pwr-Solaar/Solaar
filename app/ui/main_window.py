#
#
#

from gi.repository import (Gtk, Gdk)

import ui
from logitech.devices.constants import (STATUS, PROPS)


_SMALL_DEVICE_ICON_SIZE = Gtk.IconSize.BUTTON
_DEVICE_ICON_SIZE = Gtk.IconSize.DIALOG
_STATUS_ICON_SIZE = Gtk.IconSize.LARGE_TOOLBAR
_PLACEHOLDER = '~'

#
#
#

def _info_text(dev):
	fw_text = '\n'.join(['%-12s\t<tt>%s%s%s</tt>' %
						(f.kind, f.name, ' ' if f.name else '', f.version) for f in dev.firmware])
	return ('<small>'
			'Serial    \t\t<tt>%s</tt>\n'
			'%s'
			'</small>' % (dev.serial, fw_text))

def _toggle_info(action, label_widget, box_widget, frame):
	if action.get_active():
		box_widget.set_visible(True)
		if not label_widget.get_text():
			label_widget.set_markup(_info_text(frame._device))
	else:
		box_widget.set_visible(False)


def _make_receiver_box(name):
	frame = Gtk.Frame()
	frame._device = None

	icon = Gtk.Image.new_from_icon_name(name, _SMALL_DEVICE_ICON_SIZE)

	label = Gtk.Label('Initializing...')
	label.set_name('label')
	label.set_alignment(0, 0.5)

	toolbar = Gtk.Toolbar()
	toolbar.set_name('toolbar')
	toolbar.set_style(Gtk.ToolbarStyle.ICONS)
	toolbar.set_icon_size(Gtk.IconSize.MENU)
	toolbar.set_show_arrow(False)

	hbox = Gtk.HBox(homogeneous=False, spacing=8)
	hbox.pack_start(icon, False, False, 0)
	hbox.pack_start(label, True, True, 0)
	hbox.pack_end(toolbar, False, False, 0)

	info_label = Gtk.Label()
	info_label.set_name('info-label')
	info_label.set_alignment(0, 0.5)
	info_label.set_padding(8, 2)
	info_label.set_selectable(True)

	info_box = Gtk.Frame()
	info_box.add(info_label)
	info_box.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

	toggle_info_action = ui.action._toggle_action('info', 'Receiver info', _toggle_info, info_label, info_box, frame)
	toolbar.insert(toggle_info_action.create_tool_item(), 0)
	toolbar.insert(ui.action.pair(frame).create_tool_item(), -1)

	vbox = Gtk.VBox(homogeneous=False, spacing=2)
	vbox.set_border_width(4)
	vbox.pack_start(hbox, True, True, 0)
	vbox.pack_start(info_box, True, True, 0)

	frame.add(vbox)
	frame.show_all()
	info_box.set_visible(False)
	return frame


def _make_device_box(index):
	frame = Gtk.Frame()
	frame._device = None

	icon = Gtk.Image.new_from_icon_name('image-missing', _DEVICE_ICON_SIZE)
	icon.set_name('icon')
	icon.set_alignment(0.5, 0)

	label = Gtk.Label('Initializing...')
	label.set_name('label')
	label.set_alignment(0, 0.5)
	label.set_padding(4, 4)

	battery_icon = Gtk.Image.new_from_icon_name('battery_unknown', _STATUS_ICON_SIZE)

	battery_label = Gtk.Label()
	battery_label.set_width_chars(6)
	battery_label.set_alignment(0, 0.5)

	light_icon = Gtk.Image.new_from_icon_name('light_unknown', _STATUS_ICON_SIZE)

	light_label = Gtk.Label()
	light_label.set_alignment(0, 0.5)
	light_label.set_width_chars(8)

	toolbar = Gtk.Toolbar()
	toolbar.set_name('toolbar')
	toolbar.set_style(Gtk.ToolbarStyle.ICONS)
	toolbar.set_icon_size(Gtk.IconSize.MENU)
	toolbar.set_show_arrow(False)

	status_box = Gtk.HBox(homogeneous=False, spacing=0)
	status_box.set_name('status')
	status_box.pack_start(battery_icon, False, True, 0)
	status_box.pack_start(battery_label, False, True, 0)
	status_box.pack_start(light_icon, False, True, 0)
	status_box.pack_start(light_label, False, True, 0)
	status_box.pack_end(toolbar, False, False, 0)

	info_label = Gtk.Label()
	info_label.set_name('info-label')
	info_label.set_alignment(0, 0.5)
	info_label.set_padding(8, 2)
	info_label.set_selectable(True)

	info_box = Gtk.Frame()
	info_box.add(info_label)

	toggle_info_action = ui.action._toggle_action('info', 'Device info', _toggle_info, info_label, info_box, frame)
	toolbar.insert(toggle_info_action.create_tool_item(), 0)
	toolbar.insert(ui.action.unpair(frame).create_tool_item(), -1)

	vbox = Gtk.VBox(homogeneous=False, spacing=4)
	vbox.pack_start(label, True, True, 0)
	vbox.pack_start(status_box, True, True, 0)
	vbox.pack_start(info_box, True, True, 0)

	box = Gtk.HBox(homogeneous=False, spacing=4)
	box.set_border_width(4)
	box.pack_start(icon, False, False, 0)
	box.pack_start(vbox, True, True, 0)
	box.show_all()

	frame.add(box)
	info_box.set_visible(False)
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


def create(title, name, max_devices, systray=False):
	window = Gtk.Window()
	window.set_title(title)
	window.set_icon_name(ui.appicon(0))
	window.set_role('status-window')

	vbox = Gtk.VBox(homogeneous=False, spacing=4)
	vbox.set_border_width(4)

	rbox = _make_receiver_box(name)
	vbox.add(rbox)
	for i in range(1, 1 + max_devices):
		dbox = _make_device_box(i)
		vbox.add(dbox)
	vbox.set_visible(True)

	window.add(vbox)

	geometry = Gdk.Geometry()
	geometry.min_width = 320
	geometry.min_height = 20
	window.set_geometry_hints(vbox, geometry, Gdk.WindowHints.MIN_SIZE)
	window.set_resizable(False)

	window.toggle_visible = lambda i: toggle(window, i)

	if systray:
		window.set_keep_above(True)
		window.connect('delete-event', toggle)
	else:
		window.connect('delete-event', Gtk.main_quit)

	return window

#
#
#

def _update_receiver_box(frame, receiver):
	label, toolbar, info_label = ui.find_children(frame, 'label', 'toolbar', 'info-label')

	label.set_text(receiver.status_text or '')
	if receiver.status < STATUS.CONNECTED:
		frame._device = None
		toolbar.set_sensitive(False)
		toolbar.get_children()[0].set_active(False)
		info_label.set_text('')
	else:
		toolbar.set_sensitive(True)
		frame._device = receiver


def _update_device_box(frame, dev):
	frame._device = dev

	icon, label, info_label = ui.find_children(frame, 'icon', 'label', 'info-label')

	if frame.get_name() != dev.name:
		frame.set_name(dev.name)
		icon.set_from_icon_name(ui.get_icon(dev.name, dev.kind), _DEVICE_ICON_SIZE)
		label.set_markup('<b>' + dev.name + '</b>')

	status = ui.find_children(frame, 'status')
	status_icons = status.get_children()
	toolbar = status_icons[-1]
	if dev.status < STATUS.CONNECTED:
		icon.set_sensitive(False)
		label.set_sensitive(False)
		status.set_sensitive(False)
		for c in status_icons[1:-1]:
			c.set_visible(False)
		toolbar.get_children()[0].set_active(False)
	else:
		icon.set_sensitive(True)
		label.set_sensitive(True)
		status.set_sensitive(True)

		battery_icon, battery_label = status_icons[0:2]
		battery_level = dev.props.get(PROPS.BATTERY_LEVEL)
		if battery_level is None:
			battery_icon.set_from_icon_name('battery_unknown', _STATUS_ICON_SIZE)
			battery_icon.set_sensitive(False)
			battery_label.set_visible(False)
		else:
			icon_name = 'battery_%03d' % (20 * ((battery_level + 10) // 20))
			battery_icon.set_from_icon_name(icon_name, _STATUS_ICON_SIZE)
			battery_icon.set_sensitive(True)
			battery_label.set_text('%d%%' % battery_level)
			battery_label.set_visible(True)

		battery_status = dev.props.get(PROPS.BATTERY_STATUS)
		battery_icon.set_tooltip_text(battery_status or '')

		light_icon, light_label = status_icons[2:4]
		light_level = dev.props.get(PROPS.LIGHT_LEVEL)
		if light_level is None:
			light_icon.set_visible(False)
			light_label.set_visible(False)
		else:
			icon_name = 'light_%03d' % (20 * ((light_level + 50) // 100))
			light_icon.set_from_icon_name(icon_name, _STATUS_ICON_SIZE)
			light_icon.set_visible(True)
			light_label.set_text('%d lux' % light_level)
			light_label.set_visible(True)

		for b in toolbar.get_children()[:-1]:
			b.set_sensitive(True)

	frame.set_visible(True)


def update(window, receiver, reason):
	print ("update", receiver, receiver.status, reason)
	window.set_icon_name(ui.appicon(receiver.status))

	vbox = window.get_child()
	controls = list(vbox.get_children())

	if reason == receiver:
		_update_receiver_box(controls[0], receiver)
	else:
		frame = controls[reason.number]
		if reason.status == STATUS.UNPAIRED:
			frame.set_visible(False)
			frame.set_name(_PLACEHOLDER)
			frame._device = None
		else:
			_update_device_box(frame, reason)
