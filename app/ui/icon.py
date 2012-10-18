#
#
#

from gi.repository import Gtk


def create(title, click_action=None, actions=None):
	icon = Gtk.StatusIcon()
	icon.set_title(title)
	icon.set_name(title)

	if click_action:
		if type(click_action) == tuple:
			function = click_action[0]
			args = click_action[1:]
			icon.connect('activate', function, *args)
		else:
			icon.connect('activate', click_action)

	menu = Gtk.Menu()

	if actions:
		for name, activate, checked in actions:
			if checked is None:
				item = Gtk.MenuItem(name)
				if activate is None:
					item.set_sensitive(False)
				else:
					item.connect('activate', activate)
			else:
				item = Gtk.CheckMenuItem(name)
				if activate is None:
					item.set_sensitive(False)
				else:
					item.set_active(checked or False)
					item.connect('toggled', activate)

			menu.append(item)
		menu.append(Gtk.SeparatorMenuItem())

	quit_item = Gtk.MenuItem('Quit')
	quit_item.connect('activate', Gtk.main_quit)
	menu.append(quit_item)

	menu.show_all()

	icon.connect('popup_menu',
					lambda icon, button, time, menu:
						menu.popup(None, None, icon.position_menu, icon, button, time),
					menu)

	return icon


def update(icon, receiver, icon_name=None):
	if icon_name is not None:
		icon.set_from_icon_name(icon_name)

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
