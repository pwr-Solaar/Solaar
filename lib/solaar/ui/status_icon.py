#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from gi.repository import Gtk, GdkPixbuf

from solaar import NAME
from . import action as _action, icons as _icons
from logitech.unifying_receiver import status as _status

#
#
#

def _create_common(icon, menu_activate_callback):
	icon._devices_info = []

	icon.set_title(NAME)

	icon._menu_activate_callback = menu_activate_callback
	icon._menu = menu = Gtk.Menu()

	no_receiver = Gtk.MenuItem.new_with_label('No receiver found')
	no_receiver.set_sensitive(False)
	menu.append(no_receiver)

	# per-device menu entries will be generated as-needed
	menu.append(Gtk.SeparatorMenuItem.new())
	menu.append(_action.about.create_menu_item())
	menu.append(_action.make('application-exit', 'Quit', Gtk.main_quit).create_menu_item())
	menu.show_all()


try:
	raise ImportError
	# try:
	# 	from gi.repository import AppIndicator3 as AppIndicator
	# except ImportError:
	# 	from gi.repository import AppIndicator

	# def create(activate_callback, menu_activate_callback):
	# 	assert activate_callback
	# 	assert menu_activate_callback

	# 	ind = AppIndicator.Indicator.new('indicator-solaar', _icons.APP_ICON[0], AppIndicator.IndicatorCategory.HARDWARE)
	# 	ind.set_status(AppIndicator.IndicatorStatus.ACTIVE)

	# 	_create_common(ind, menu_activate_callback)
	# 	ind.set_menu(ind._menu)

	# 	return ind


	# def destroy(ind):
	# 	ind.set_status(AppIndicator.IndicatorStatus.PASSIVE)
	# 	ind.set_menu(None)


	# def _update_icon_tooltip(ind, lines_generator):
	# 	pass


	# def _update_icon_image(ind, image):
	# 	if isinstance(image, GdkPixbuf.Pixbuf):
	# 		pass
	# 	else:
	# 		ind.set_icon(image)

except ImportError:

	def create(activate_callback, menu_activate_callback):
		assert activate_callback
		assert menu_activate_callback

		icon = Gtk.StatusIcon.new_from_icon_name(_icons.APP_ICON[0])
		icon.set_name(NAME)
		icon.set_tooltip_text(NAME)
		icon.connect('activate', activate_callback)

		_create_common(icon, menu_activate_callback)
		icon.connect('popup_menu',
						lambda icon, button, time, menu:
							icon._menu.popup(None, None, icon.position_menu, icon, button, time),
						icon._menu)

		return icon


	def destroy(icon):
		icon.set_visible(False)


	def _update_icon_tooltip(icon, lines_generator):
		tooltip_lines = lines_generator(icon)
		icon.set_tooltip_markup('\n'.join(tooltip_lines).rstrip('\n'))


	def _update_icon_image(icon, image):
		if isinstance(image, GdkPixbuf.Pixbuf):
			icon.set_from_pixbuf(image)
		else:
			icon.set_from_icon_name(image)

#
#
#

def _generate_tooltip_lines(icon):
	yield '<b>%s</b>' % NAME
	yield ''

	for _, serial, name, status in icon._devices_info:
		yield '<b>%s</b>' % name

		p = str(status)
		if p:  # does it have any properties to print?
			if status:
				yield '\t%s' % p
			else:
				yield '\t%s <small>(inactive)</small>' % p
		else:
			if status:
				yield '\t<small>no status</small>'
			else:
				yield '\t<small>(inactive)</small>'
		yield ''


_PIXMAPS = {}
def _icon_with_battery(level, active):
	battery_icon = _icons.battery(level)
	name = '%s-%s' % (battery_icon, active)
	if name not in _PIXMAPS:
		mask = _icons.icon_file(_icons.APP_ICON[2], 128)
		if not mask:
			return
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


def _generate_image(icon):
	if not icon._devices_info:
		return _icons.APP_ICON[-1]

	battery_status = None
	battery_level = 1000

	for _, serial, name, status in icon._devices_info:
		if serial is None: # is receiver
			continue
		level = status.get(_status.BATTERY_LEVEL)
		if level is not None and level < battery_level:
			battery_status = status
			battery_level = level

	if battery_status is None:
		return _icons.APP_ICON[1]
	else:
		pixbuf = _icon_with_battery(battery_level, bool(battery_status))
		if pixbuf:
			return pixbuf
		else:
			return _icons.APP_ICON[1]

#
#
#

def _add_device(icon, device):
	index = len(icon._devices_info)
	device_info = (device.receiver.serial, device.serial, device.name, device.status)
	icon._devices_info.append(device_info)

	menu_item = Gtk.ImageMenuItem.new_with_label('  ' + device.name)
	icon._menu.insert(menu_item, index)
	menu_item.set_image(Gtk.Image())
	menu_item.show_all()
	menu_item.connect('activate', icon._menu_activate_callback, device.receiver.path, icon)

	return index


def _remove_device(icon, index):
	# print ("remove device", index)
	assert index is not None
	del icon._devices_info[index]
	menu_items = icon._menu.get_children()
	icon._menu.remove(menu_items[index])


def _add_receiver(icon, receiver):
	device_info = (receiver.serial, None, receiver.name, None)
	icon._devices_info.insert(0, device_info)

	menu_item = Gtk.ImageMenuItem.new_with_label(receiver.name)
	icon._menu.insert(menu_item, 0)
	menu_item.set_image(Gtk.Image().new_from_icon_name(receiver.name, Gtk.IconSize.LARGE_TOOLBAR))
	menu_item.show_all()
	menu_item.connect('activate', icon._menu_activate_callback, receiver.path, icon)

	return 0


def _remove_receiver(icon, receiver):
	index = 0
	while index < len(icon._devices_info):
		rserial, _, _, _ = icon._devices_info[index]
		# print ("remove receiver", index, rserial)
		if rserial == receiver.serial:
			_remove_device(icon, index)
		else:
			index += 1


def _update_menu_item(icon, index, device_status):
	menu_items = icon._menu.get_children()
	menu_item = menu_items[index]

	image = menu_item.get_image()
	battery_level = device_status.get(_status.BATTERY_LEVEL)
	print ("device_status", dict(device_status), battery_level)
	image.set_from_icon_name(_icons.battery(battery_level), Gtk.IconSize.LARGE_TOOLBAR)
	image.set_sensitive(bool(device_status))
	# menu_item.set_sensitive(bool(device_status))

#
#
#

def update(icon, device=None):
	# print ("icon update", device)

	if device is not None:
		if device.kind is None:
			# receiver
			receiver = device
			if receiver:
				index = None
				for idx, (rserial, _, _, _) in enumerate(icon._devices_info):
					if rserial == receiver.serial:
						index = idx
						break

				if index is None:
					_add_receiver(icon, receiver)
			else:
				_remove_receiver(icon, receiver)

		else:
			# peripheral
			index = None
			for idx, (rserial, serial, name, _) in enumerate(icon._devices_info):
				if rserial == device.receiver.serial and serial == device.serial:
					index = idx

			if device.status is None:
				# was just unpaired
				assert index is not None
				_remove_device(icon, index)
			else:
				if index is None:
					index = _add_device(icon, device)
				_update_menu_item(icon, index, device.status)

		menu_items = icon._menu.get_children()
		menu_items[len(icon._devices_info)].set_visible(not icon._devices_info)

	_update_icon_tooltip(icon, _generate_tooltip_lines)
	_update_icon_image(icon, _generate_image(icon))
