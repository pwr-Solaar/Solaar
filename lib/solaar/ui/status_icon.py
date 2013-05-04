#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from gi.repository import Gtk, GdkPixbuf

from . import (action as _action,
				icons as _icons,
				main_window as _main_window)
from solaar import NAME
from logitech.unifying_receiver import status as _status

#
#
#

_NO_DEVICES = [None] * 6

def create(window):

	icon = Gtk.StatusIcon()
	icon.set_title(NAME)
	icon.set_name(NAME)
	icon.set_from_icon_name(_icons.APP_ICON[0])
	icon._devices = list(_NO_DEVICES)

	icon.connect('activate', _main_window.toggle, window)
	icon.set_tooltip_text(NAME)

	menu = Gtk.Menu()

	menu.append(Gtk.SeparatorMenuItem.new())

	menu.append(_action.about.create_menu_item())
	menu.append(_action.make('application-exit', 'Quit', Gtk.main_quit).create_menu_item())
	menu.show_all()

	for x in _NO_DEVICES:
		m = Gtk.ImageMenuItem()
		m.set_sensitive(False)
		menu.insert(m, 0)

	icon.connect('popup_menu',
					lambda icon, button, time, menu:
						menu.popup(None, None, icon.position_menu, icon, button, time),
					menu)
	return icon


_PIXMAPS = {}
def _icon_with_battery(level, active):
	battery_icon = _icons.battery(level)
	name = '%s-%s' % (battery_icon, active)
	if name not in _PIXMAPS:
		mask = _icons.icon_file(_icons.APP_ICON[2], 128)
		assert mask
		mask = GdkPixbuf.Pixbuf.new_from_file(mask)
		assert mask.get_width() == 128 and mask.get_height() == 128
		mask.saturate_and_pixelate(mask, 0.7, False)

		battery = _icons.icon_file(battery_icon, 128)
		assert battery
		battery = GdkPixbuf.Pixbuf.new_from_file(battery)
		assert battery.get_width() == 128 and battery.get_height() == 128
		if not active:
			battery.saturate_and_pixelate(battery, 0, True)

		# TODO can the masking be done at runtime?
		battery.composite(mask, 0, 7, 80, 121, -32, 7, 1, 1, GdkPixbuf.InterpType.NEAREST, 255)
		_PIXMAPS[name] = mask

	return _PIXMAPS[name]

def update(icon, device):
	assert device is not None
	# print ("icon update", device)

	if device.kind is None:
		receiver = device
		if not device:
			icon._devices[:] = _NO_DEVICES
	else:
		icon._devices[device.number] = None if device.status is None else device
		receiver = device.receiver

	if not icon.is_embedded():
		return

	def _lines(r, devices):
		yield '<b>%s</b>: %s' % (NAME, r.status)
		yield ''

		for dev in devices:
			if dev is None:
				continue

			yield '<b>%s</b>' % dev.name

			assert hasattr(dev, 'status') and dev.status is not None
			p = str(dev.status)
			if p:  # does it have any properties to print?
				if dev.status:
					yield '\t%s' % p
				else:
					yield '\t%s <small>(inactive)</small>' % p
			else:
				if dev.status:
					yield '\t<small>no status</small>'
				else:
					yield '\t<small>(inactive)</small>'
			yield ''

	icon.set_tooltip_markup('\n'.join(_lines(receiver, icon._devices)).rstrip('\n'))

	battery_status = None
	battery_level = 1000
	for dev in icon._devices:
		if dev is not None:
			level = dev.status.get(_status.BATTERY_LEVEL)
			if level is not None and level < battery_level:
				battery_status = dev.status
				battery_level = level

	if battery_status is None:
		icon.set_from_icon_name(_icons.APP_ICON[1 if receiver else -1])
	else:
		icon.set_from_pixbuf(_icon_with_battery(battery_level, bool(battery_status)))
