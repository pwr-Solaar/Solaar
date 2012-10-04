#
#
#

from gi.repository import Gtk
from gi.repository import Gdk


_DEVICE_ICON_SIZE = Gtk.IconSize.DIALOG
_STATUS_ICON_SIZE = Gtk.IconSize.DIALOG
_PLACEHOLDER = '~'
_MAX_DEVICES = 6


def update(window, devices):
	if not window or not window.get_child():
		return

	controls = list(window.get_child().get_children())

	first = controls[0].get_child()
	icon, label = first.get_children()
	rstatus = devices[0]
	label.set_markup('<big><b>%s</b></big>\n%s' % (rstatus.name, rstatus.text))

	for index in range(1, 1 + _MAX_DEVICES):
		devstatus = devices.get(index)
		controls[index].set_visible(devstatus is not None)

		box = controls[index].get_child()
		icon, expander = box.get_children()

		if devstatus:
			if icon.get_name() != devstatus.name:
				icon.set_name(devstatus.name)
				icon.set_from_icon_name(devstatus.name, _DEVICE_ICON_SIZE)

			if devstatus.code < 0:
				expander.set_sensitive(False)
				expander.set_expanded(False)
				expander.set_label('<big><b>%s</b></big>\n%s' % (devstatus.name, devstatus.text))
			else:
				expander.set_sensitive(True)
				ebox = expander.get_child()

				texts = []

				light_icon = ebox.get_children()[-2]
				light_level = getattr(devstatus, 'light_level', None)
				light_icon.set_visible(light_level is not None)
				if light_level is not None:
					texts.append('Light: %d lux' % light_level)
					icon_name = 'light_%02d' % (20 * ((light_level + 50) // 100))
					light_icon.set_from_icon_name(icon_name, _STATUS_ICON_SIZE)
					light_icon.set_tooltip_text(texts[-1])

				battery_icon = ebox.get_children()[-1]
				battery_level = getattr(devstatus, 'battery_level', None)
				battery_icon.set_sensitive(battery_level is not None)
				if battery_level is None:
					battery_icon.set_from_icon_name('battery_unknown', _STATUS_ICON_SIZE)
					battery_icon.set_tooltip_text('Battery: unknown')
				else:
					texts.append('Battery: %d%%' % battery_level)
					icon_name = 'battery_%02d' % (20 * ((battery_level + 10) // 20))
					battery_icon.set_from_icon_name(icon_name, _STATUS_ICON_SIZE)
					battery_icon.set_tooltip_text(texts[-1])

				battery_status = getattr(devstatus, 'battery_status', None)
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


def _device_box(title):
	icon = Gtk.Image.new_from_icon_name(title, _DEVICE_ICON_SIZE)
	icon.set_alignment(0.5, 0)
	icon.set_name(title)

	box = Gtk.HBox(homogeneous=False, spacing=8)
	box.pack_start(icon, False, False, 0)
	box.set_border_width(8)

	if title == _PLACEHOLDER:
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
	else:
		label = Gtk.Label()
		label.set_can_focus(False)
		label.set_markup('<big><b>%s</b></big>' % title)
		label.set_alignment(0, 0)
		box.add(label)

	frame = Gtk.Frame()
	frame.add(box)
	frame.show_all()
	frame.set_visible(title != _PLACEHOLDER)
	return frame


def create(title, rstatus):
	vbox = Gtk.VBox(homogeneous=False, spacing=4)
	vbox.set_border_width(4)

	vbox.add(_device_box(rstatus.name))
	for i in range(1, 1 + _MAX_DEVICES):
		vbox.add(_device_box(_PLACEHOLDER))
	vbox.set_visible(True)

	window = Gtk.Window()
	window.set_title(title)
	window.set_icon_name(title)
	window.set_keep_above(True)
	# window.set_skip_taskbar_hint(True)
	# window.set_skip_pager_hint(True)
	window.set_deletable(False)
	window.set_resizable(False)
	window.set_position(Gtk.WindowPosition.MOUSE)
	window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
	window.set_wmclass(title, 'status-window')
	window.set_role('status-window')

	window.connect('window-state-event', _state_event)
	window.connect('delete-event', lambda w, e: toggle(None, window) or True)

	window.add(vbox)
	window.present()
	return window


def _state_event(window, event):
	if event.new_window_state & Gdk.WindowState.ICONIFIED:
		position = window.get_position()
		window.hide()
		window.deiconify()
		window.move(*position)
		return True

def toggle(_, window):
	if window.get_visible():
		position = window.get_position()
		window.hide()
		window.move(*position)
	else:
		window.present()
