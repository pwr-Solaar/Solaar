#
#
#

from gi.repository import Gtk


def _show_icon_menu(icon, button, time, menu):
	menu.popup(None, None, icon.position_menu, icon, button, time)


def create(title, menu_actions, click_action=None):
	icon = Gtk.StatusIcon.new_from_icon_name(title)
	icon.set_title(title)
	icon.set_name(title)

	if click_action:
		if type(click_action) == tuple:
			function = click_action[0]
			args = click_action[1:]
			icon.connect('activate', function, *args)
		else:
			icon.connect('activate', click_action)

	if menu_actions:
		if type(menu_actions) == list:
			menu = Gtk.Menu()
			for action in menu_actions:
				if action:
					item = Gtk.MenuItem(action[0])
					args = action[2:] if len(action) > 2 else ()
					item.connect('activate', action[1], *args)
				else:
					item = Gtk.SeparatorMenuItem()
				menu.append(item)
			menu.show_all()
			icon.connect('popup_menu', _show_icon_menu, menu)
		else:
			icon.connect('popup_menu', menu_actions)

	return icon
