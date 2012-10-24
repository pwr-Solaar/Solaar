#
#
#

from gi.repository import Gtk
import ui


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
	icon.set_from_icon_name(ui.appicon(receiver.status))

	if receiver.devices:
		lines = []
		if receiver.status < 1:
			lines += (receiver.status_text, '')

		devlist = [receiver.devices[d] for d in range(1, 1 + receiver.max_devices) if d in receiver.devices]
		for dev in devlist:
			name = '<b>' + dev.name + '</b>'
			if dev.status < 1:
				lines.append(name + ' (' + dev.status_text + ')')
			else:
				lines.append(name)
				if dev.status > 1:
					lines.append('    ' + dev.status_text)
			lines.append('')

		text = '\n'.join(lines).rstrip('\n')
		icon.set_tooltip_markup(text)
	else:
		icon.set_tooltip_text(receiver.status_text)
