#
#
#

from gi.repository import Gtk
from gi.repository import Gdk

from logitech.devices import constants as C


_DEVICE_ICON_SIZE = Gtk.IconSize.DIALOG
_STATUS_ICON_SIZE = Gtk.IconSize.DIALOG
_PLACEHOLDER = '~'
_MAX_DEVICES = 6


def _update_receiver_box(box, receiver):
	icon, vbox = box.get_children()
	label, buttons_box = vbox.get_children()
	label.set_text(receiver.text or '')
	buttons_box.set_visible(receiver.code >= C.STATUS.CONNECTED)


def _update_device_box(frame, devstatus):
	frame.set_visible(devstatus is not None)

	box = frame.get_child()
	icon, expander = box.get_children()

	if devstatus:
		if icon.get_name() != devstatus.name:
			icon.set_name(devstatus.name)
			icon.set_from_icon_name(devstatus.name, _DEVICE_ICON_SIZE)

		if devstatus.code < C.STATUS.CONNECTED:
			expander.set_sensitive(False)
			expander.set_expanded(False)
			expander.set_label('<big><b>%s</b></big>\n%s' % (devstatus.name, devstatus.text))
		else:
			expander.set_sensitive(True)
			ebox = expander.get_child()

			texts = []

			light_icon = ebox.get_children()[-2]
			light_level = getattr(devstatus, C.PROPS.LIGHT_LEVEL, None)
			light_icon.set_visible(light_level is not None)
			if light_level is not None:
				texts.append('Light: %d lux' % light_level)
				icon_name = 'light_%02d' % (20 * ((light_level + 50) // 100))
				light_icon.set_from_icon_name(icon_name, _STATUS_ICON_SIZE)
				light_icon.set_tooltip_text(texts[-1])

			battery_icon = ebox.get_children()[-1]
			battery_level = getattr(devstatus, C.PROPS.BATTERY_LEVEL, None)
			battery_icon.set_sensitive(battery_level is not None)
			if battery_level is None:
				battery_icon.set_from_icon_name('battery_unknown', _STATUS_ICON_SIZE)
				battery_icon.set_tooltip_text('Battery: unknown')
			else:
				texts.append('Battery: %d%%' % battery_level)
				icon_name = 'battery_%02d' % (20 * ((battery_level + 10) // 20))
				battery_icon.set_from_icon_name(icon_name, _STATUS_ICON_SIZE)
				battery_icon.set_tooltip_text(texts[-1])

			battery_status = getattr(devstatus, C.PROPS.BATTERY_STATUS, None)
			if battery_status is not None:
				texts.append(battery_status)
				battery_icon.set_tooltip_text(battery_icon.get_tooltip_text() + '\n' + battery_status)

			if texts:
				expander.set_label('<big><b>%s</b></big>\n%s' % (devstatus.name, ', '.join(texts)))
			else:
				expander.set_label('<big><b>%s</b></big>\n%s' % (devstatus.name, devstatus.text))
	else:
		icon.set_name(_PLACEHOLDER)
		expander.set_label(_PLACEHOLDER)


def update(window, receiver, devices):
	if window and window.get_child():
		controls = list(window.get_child().get_children())
		_update_receiver_box(controls[0], receiver)
		for index in range(1, 1 + _MAX_DEVICES):
			_update_device_box(controls[index], devices.get(index))


def _receiver_box(rstatus):
	box = Gtk.HBox(homogeneous=False, spacing=8)
	box.set_border_width(8)

	icon = Gtk.Image.new_from_icon_name(rstatus.name, _DEVICE_ICON_SIZE)
	icon.set_alignment(0.5, 0)
	icon.set_name(rstatus.name)
	box.pack_start(icon, False, False, 0)

	vbox = Gtk.VBox(homogeneous=False, spacing=4)
	box.pack_start(vbox, True, True, 0)

	label = Gtk.Label()
	label.set_can_focus(False)
	label.set_alignment(0, 0)
	vbox.pack_start(label, False, False, 0)

	buttons_box = Gtk.HButtonBox()
	buttons_box.set_spacing(8)
	buttons_box.set_layout(Gtk.ButtonBoxStyle.START)
	vbox.pack_start(buttons_box, True, True, 0)

	def _action(button, action):
		button.set_sensitive(False)
		action()
		button.set_sensitive(True)

	def _add_button(name, icon, action):
		button = Gtk.Button(name.split(' ')[0])
		button.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
		button.set_relief(Gtk.ReliefStyle.HALF)
		button.set_tooltip_text(name)
		button.set_focus_on_click(False)
		if action:
			button.connect('clicked', _action, action)
		else:
			button.set_sensitive(False)
		buttons_box.pack_start(button, False, False, 0)

	_add_button('Scan for devices', 'reload', rstatus.refresh)
	_add_button('Pair new device', 'add', rstatus.pair)

	box.show_all()
	return box


def _device_box():
	icon = Gtk.Image()
	icon.set_alignment(0.5, 0)
	icon.set_name(_PLACEHOLDER)

	box = Gtk.HBox(homogeneous=False, spacing=8)
	box.pack_start(icon, False, False, 0)
	box.set_border_width(8)

	expander = Gtk.Expander()
	expander.set_can_focus(False)
	expander.set_label(_PLACEHOLDER)
	expander.set_use_markup(True)
	expander.set_spacing(4)

	ebox = Gtk.HBox(False, 8)

	battery_icon = Gtk.Image.new_from_icon_name('battery_unknown', _STATUS_ICON_SIZE)
	ebox.pack_end(battery_icon, False, True, 0)

	light_icon = Gtk.Image.new_from_icon_name('light_unknown', _STATUS_ICON_SIZE)
	ebox.pack_end(light_icon, False, True, 0)

	expander.add(ebox)
	box.pack_start(expander, True, True, 1)

	frame = Gtk.Frame()
	frame.add(box)
	frame.show_all()
	frame.set_visible(False)
	return frame


def create(title, rstatus, show=True, close_to_tray=False):
	window = Gtk.Window()

	Gtk.Window.set_default_icon_name('mouse')
	window.set_icon_name(title)

	window.set_title(title)
	window.set_keep_above(True)
	window.set_deletable(False)
	window.set_resizable(False)
	window.set_size_request(200, 50)
	window.set_default_size(200, 50)

	window.set_position(Gtk.WindowPosition.MOUSE)
	window.set_type_hint(Gdk.WindowTypeHint.UTILITY)

	# window.set_skip_taskbar_hint(True)
	# window.set_skip_pager_hint(True)
	# window.set_wmclass(title, 'status-window')
	# window.set_role('status-window')

	vbox = Gtk.VBox(homogeneous=False, spacing=4)
	vbox.set_border_width(4)

	vbox.add(_receiver_box(rstatus))
	for i in range(1, 1 + _MAX_DEVICES):
		vbox.add(_device_box())
	vbox.set_visible(True)
	window.add(vbox)

	if close_to_tray:
		def _state_event(window, event):
			if event.new_window_state & Gdk.WindowState.ICONIFIED:
				position = window.get_position()
				window.hide()
				window.deiconify()
				window.move(*position)
				return True

		window.connect('window-state-event', _state_event)
		window.connect('delete-event', lambda w, e: toggle(None, window) or True)
	else:
		window.connect('delete-event', Gtk.main_quit)

	if show:
		window.present()
	return window


def toggle(_, window):
	if window.get_visible():
		position = window.get_position()
		window.hide()
		window.move(*position)
	else:
		window.present()
