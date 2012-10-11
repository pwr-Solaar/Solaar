#
#
#

from gi.repository import (Gtk, Gdk)

from logitech.devices import constants as C


_DEVICE_ICON_SIZE = Gtk.IconSize.DND
_STATUS_ICON_SIZE = Gtk.IconSize.DIALOG
_PLACEHOLDER = '~'


def _find_children(container, *child_names):
	def _iterate_children(widget, names, result, count):
		wname = widget.get_name()
		if wname in names:
			index = names.index(wname)
			names[index] = None
			result[index] = widget
			count -= 1

		if count > 0 and isinstance(widget, Gtk.Container):
			for w in widget:
				count = _iterate_children(w, names, result, count)
				if count == 0:
					break

		return count

	names = list(child_names)
	count = len(names)
	result = [None] * count
	_iterate_children(container, names, result, count)
	return result if count > 1 else result[0]


def _update_receiver_box(box, receiver):
	label, buttons_box = _find_children(box, 'receiver-status', 'receiver-buttons')
	label.set_text(receiver.text or '')
	buttons_box.set_visible(receiver.code >= C.STATUS.CONNECTED)


def _update_device_box(frame, devstatus):
	if devstatus is None:
		frame.set_visible(False)
		frame.set_name(_PLACEHOLDER)
		return

	frame.set_visible(True)
	if frame.get_name() != devstatus.name:
		frame.set_name(devstatus.name)
		icon = _find_children(frame, 'device-icon')
		icon.set_from_icon_name(devstatus.name, _DEVICE_ICON_SIZE)
		icon.set_tooltip_text(devstatus.name)

	expander = _find_children(frame, 'device-expander')
	if devstatus.code < C.STATUS.CONNECTED:
		expander.set_sensitive(False)
		expander.set_expanded(False)
		expander.set_label('<big><b>%s</b></big>\n%s' % (devstatus.name, devstatus.text))
		return

	expander.set_sensitive(True)
	status_icons = expander.get_child().get_children()

	texts = []

	light_icon = status_icons[-2]
	light_level = getattr(devstatus, C.PROPS.LIGHT_LEVEL, None)
	if light_level is None:
		light_icon.set_visible(False)
	else:
		light_icon.set_visible(True)
		icon_name = 'light_%02d' % (20 * ((light_level + 50) // 100))
		light_icon.set_from_icon_name(icon_name, _STATUS_ICON_SIZE)
		tooltip = 'Light: %d lux' % light_level
		light_icon.set_tooltip_text(tooltip)
		texts.append(tooltip)

	battery_icon = status_icons[-1]
	battery_level = getattr(devstatus, C.PROPS.BATTERY_LEVEL, None)
	if battery_level is None:
		battery_icon.set_sensitive(False)
		battery_icon.set_from_icon_name('battery_unknown', _STATUS_ICON_SIZE)
		battery_icon.set_tooltip_text('Battery: unknown')
	else:
		battery_icon.set_sensitive(True)
		icon_name = 'battery_%02d' % (20 * ((battery_level + 10) // 20))
		battery_icon.set_from_icon_name(icon_name, _STATUS_ICON_SIZE)
		tooltip = 'Battery: %d%%' % battery_level
		battery_icon.set_tooltip_text(tooltip)
		texts.append(tooltip)

	battery_status = getattr(devstatus, C.PROPS.BATTERY_STATUS, None)
	if battery_status is not None:
		texts.append(battery_status)
		battery_icon.set_tooltip_text(battery_icon.get_tooltip_text() + '\n' + battery_status)

	if texts:
		expander.set_label('<big><b>%s</b></big>\n%s' % (devstatus.name, ', '.join(texts)))
	else:
		expander.set_label('<big><b>%s</b></big>\n%s' % (devstatus.name, devstatus.text))


def update(window, receiver, devices, icon_name=None):
	if window and window.get_child():
		if icon_name is not None:
			window.set_icon_name(icon_name)

		controls = list(window.get_child().get_children())
		_update_receiver_box(controls[0], receiver)
		for index in range(1, len(controls)):
			_update_device_box(controls[index], devices.get(index))


def _receiver_box(rstatus):
	box = Gtk.HBox(homogeneous=False, spacing=8)
	box.set_border_width(4)

	icon = Gtk.Image.new_from_icon_name(rstatus.name, _DEVICE_ICON_SIZE)
	icon.set_alignment(0.5, 0)
	icon.set_tooltip_text(rstatus.name)
	box.pack_start(icon, False, False, 0)

	label = Gtk.Label('Initializing...')
	label.set_alignment(0, 0.5)
	label.set_name('receiver-status')
	box.pack_start(label, True, True, 0)

	toolbar = Gtk.Toolbar()
	toolbar.set_style(Gtk.ToolbarStyle.ICONS)
	toolbar.set_name('receiver-buttons')
	toolbar.set_show_arrow(False)
	toolbar.set_icon_size(Gtk.IconSize.BUTTON)
	box.pack_end(toolbar, False, False, 0)

	def _action(button, function, params):
		button.set_sensitive(False)
		function(button, *params)
		button.set_sensitive(True)

	def _add_button(name, icon, action):
		button = Gtk.ToolButton()
		button.set_icon_name(icon)
		button.set_tooltip_text(name)
		if action:
			function = action[0]
			params = action[1:]
			button.connect('clicked', _action, function, params)
		else:
			button.set_sensitive(False)
		toolbar.insert(button, -1)

	_add_button('Scan for devices', 'reload', rstatus.refresh)
	_add_button('Pair new device', 'add', rstatus.pair)

	box.show_all()
	toolbar.set_visible(False)
	return box


def _device_box():
	box = Gtk.HBox(homogeneous=False, spacing=8)
	box.set_border_width(4)

	icon = Gtk.Image()
	icon.set_alignment(0.5, 0)
	icon.set_name('device-icon')
	box.pack_start(icon, False, False, 0)

	expander = Gtk.Expander()
	expander.set_use_markup(True)
	expander.set_spacing(4)
	expander.set_name('device-expander')
	box.pack_start(expander, True, True, 1)

	ebox = Gtk.HBox(False, 8)
	battery_icon = Gtk.Image.new_from_icon_name('battery_unknown', _STATUS_ICON_SIZE)
	ebox.pack_end(battery_icon, False, True, 0)
	light_icon = Gtk.Image.new_from_icon_name('light_unknown', _STATUS_ICON_SIZE)
	ebox.pack_end(light_icon, False, True, 0)
	expander.add(ebox)

	frame = Gtk.Frame()
	frame.add(box)
	frame.show_all()
	frame.set_visible(False)
	return frame


def create(title, rstatus, systray=False):
	window = Gtk.Window()
	window.set_title(title)
	window.set_role('status-window')

	vbox = Gtk.VBox(homogeneous=False, spacing=4)
	vbox.set_border_width(4)

	vbox.add(_receiver_box(rstatus))
	for i in range(1, 1 + rstatus.max_devices):
		vbox.add(_device_box())
	vbox.set_visible(True)
	window.add(vbox)

	geometry = Gdk.Geometry()
	geometry.min_width = 300
	geometry.min_height = 40
	window.set_geometry_hints(vbox, geometry, Gdk.WindowHints.MIN_SIZE)

	window.set_resizable(False)
	window.set_default_size(geometry.min_width, geometry.min_height)

	if systray:
		window.set_keep_above(True)
		window.set_deletable(False)
		window.set_decorated(False)
		window.set_position(Gtk.WindowPosition.MOUSE)
		window.set_type_hint(Gdk.WindowTypeHint.MENU)
		window.set_skip_taskbar_hint(True)
		window.set_skip_pager_hint(True)
	else:
		window.set_position(Gtk.WindowPosition.CENTER)
		window.connect('delete-event', Gtk.main_quit)
		window.present()

	return window


def toggle(_, window):
	if window.get_visible():
		window.hide()
	else:
		window.present()
