#
#
#

from gi.repository import Gtk

from logitech.devices import constants as C

_ICON_OK = 'Solaar'
_ICON_FAIL = _ICON_OK + '-fail'


def create(title, click_action=None):
	icon = Gtk.StatusIcon.new_from_icon_name(_ICON_OK)
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
	item = Gtk.MenuItem('Quit')
	item.connect('activate', Gtk.main_quit)
	menu.append(item)
	menu.show_all()

	icon.connect('popup_menu',
					lambda icon, button, time, menu:
						menu.popup(None, None, icon.position_menu, icon, button, time),
					menu)

	return icon


def update(icon, receiver, tooltip):
	icon.set_tooltip_markup(tooltip)
	if receiver.code < C.STATUS.CONNECTED:
		icon.set_from_icon_name(_ICON_FAIL)
	else:
		icon.set_from_icon_name(_ICON_OK)
