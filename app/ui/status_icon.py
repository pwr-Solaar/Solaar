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
		appicon = ui.icon_file(ui.appicon(True) + '-mask')
		assert appicon
		pbuf = GdkPixbuf.Pixbuf.new_from_file(appicon)
		assert pbuf.get_width() == 128 and pbuf.get_height() == 128

		baticon = ui.icon_file(ui.get_battery_icon(battery_level))
		assert baticon
		pbuf2 = GdkPixbuf.Pixbuf.new_from_file(baticon)
		assert pbuf2.get_width() == 128 and pbuf2.get_height() == 128

		pbuf2.composite(pbuf, 0, 7, 80, 121, -32, 7, 1, 1, GdkPixbuf.InterpType.NEAREST, 255)
		icon.set_from_pixbuf(pbuf)
