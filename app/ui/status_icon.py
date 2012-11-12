#
#
#

from gi.repository import Gtk
import ui
from logitech.devices.constants import (STATUS, PROPS)


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


def update(icon, receiver):
	battery_level = None

	lines = [ui.NAME + ': ' + receiver.status_text, '']

	if receiver.status > STATUS.CONNECTED:
		devlist = sorted(receiver.devices.values(), key=lambda x: x.number)
		for dev in devlist:
			lines.append('<b>' + dev.name + '</b>')

			p = dev.properties_text
			if p:
				p = '\t' + p
				if dev.status < STATUS.CONNECTED:
					p += ' (<small>' + dev.status_text + '</small>)'
				lines.append(p)
			elif dev.status < STATUS.CONNECTED:
				lines.append('\t(<small>' + dev.status_text + '</small>)')
			elif dev.protocol < 2.0:
				lines.append('\t' + '<small>no status</small>')
			else:
				lines.append('\t' + '<small>waiting for status...</small>')

			lines.append('')

			if battery_level is None:
				if PROPS.BATTERY_LEVEL in dev.props:
					battery_level = dev.props[PROPS.BATTERY_LEVEL]

	icon.set_tooltip_markup('\n'.join(lines).rstrip('\n'))

	if battery_level is None:
		icon.set_from_icon_name(ui.appicon(receiver.status))
	else:
		icon.set_from_icon_name(ui.get_battery_icon(battery_level))
