#
#
#

from gi.repository import Gtk, GdkPixbuf

import ui
from logitech.unifying_receiver import status as _status


def create(window, menu_actions=None):
	name = window.get_title()
	icon = Gtk.StatusIcon()
	icon.set_title(name)
	icon.set_name(name)
	icon.set_from_icon_name(ui.appicon(False))
	icon._devices = {}

	icon.set_tooltip_text(name)
	icon.connect('activate', window.toggle_visible)

	menu = Gtk.Menu()
	for action in menu_actions or ():
		if action:
			menu.append(action.create_menu_item())

	menu.append(ui.action.quit.create_menu_item())
	menu.show_all()

	icon.connect('popup_menu',
					lambda icon, button, time, menu:
						menu.popup(None, None, icon.position_menu, icon, button, time),
					menu)

	return icon


_PIXMAPS = {}
def _icon_with_battery(s):
	battery_icon = ui.get_battery_icon(s[_status.BATTERY_LEVEL])

	name = '%s-%s' % (battery_icon, bool(s))
	if name not in _PIXMAPS:
		mask = ui.icon_file(ui.appicon(True) + '-mask', 128)
		assert mask
		mask = GdkPixbuf.Pixbuf.new_from_file(mask)
		assert mask.get_width() == 128 and mask.get_height() == 128
		mask.saturate_and_pixelate(mask, 0.7, False)

		battery = ui.icon_file(battery_icon, 128)
		assert battery
		battery = GdkPixbuf.Pixbuf.new_from_file(battery)
		assert battery.get_width() == 128 and battery.get_height() == 128
		if not s:
			battery.saturate_and_pixelate(battery, 0, True)

		# TODO can the masking be done at runtime?
		battery.composite(mask, 0, 7, 80, 121, -32, 7, 1, 1, GdkPixbuf.InterpType.NEAREST, 255)
		_PIXMAPS[name] = mask

	return _PIXMAPS[name]

def update(icon, receiver, device=None):
	# print ("icon update", receiver, receiver.status, len(receiver._devices), device)
	battery_status = None

	if device:
		icon._devices[device.number] = None if device.status is None else device

	lines = [ui.NAME + ': ' + str(receiver.status), '']
	if receiver:
		for k in range(1, 1 + receiver.max_devices):
			dev = icon._devices.get(k)
			if dev is None:
				continue

			lines.append('<b>' + dev.name + '</b>')

			assert hasattr(dev, 'status') and dev.status is not None
			p = str(dev.status)
			if p:
				if not dev.status:
					p += ' <small>(inactive)</small>'
			else:
				if dev.status:
					if dev.protocol < 2.0:
						p = '<small>no status</small>'
					else:
						p = '<small>waiting for status...</small>'
				else:
					p = '<small>(inactive)</small>'

			lines.append('\t' + p)
			lines.append('')

			if battery_status is None and dev.status.get(_status.BATTERY_LEVEL):
				battery_status = dev.status
	else:
		icon._devices.clear()

	icon.set_tooltip_markup('\n'.join(lines).rstrip('\n'))

	if battery_status is None:
		icon.set_from_icon_name(ui.appicon(receiver.status))
	else:
		icon.set_from_pixbuf(_icon_with_battery(battery_status))
