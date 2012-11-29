#
#
#

from gi.repository import Gtk

import ui
from logitech.unifying_receiver import status as _status


def create(window, menu_actions=None):
	icon = Gtk.StatusIcon()
	icon.set_title(window.get_title())
	icon.set_name(window.get_title())
	icon.set_from_icon_name(ui.appicon(0))

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


def update(icon, receiver, device=None):
	# print "icon update", receiver, receiver._devices, device
	battery_level = None

	lines = [ui.NAME + ': ' + str(receiver.status), '']
	if receiver and receiver._devices:
		for dev in receiver:
			lines.append('<b>' + dev.name + '</b>')

			assert dev.status is not None
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

			if battery_level is None:
				battery_level = dev.status.get(_status.BATTERY_LEVEL)

	icon.set_tooltip_markup('\n'.join(lines).rstrip('\n'))

	if battery_level is None:
		icon.set_from_icon_name(ui.appicon(receiver.status))
	else:
		icon.set_from_icon_name(ui.get_battery_icon(battery_level))
