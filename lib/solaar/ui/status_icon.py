#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from gi.repository import Gtk

from solaar import NAME
from . import action as _action, icons as _icons
from logitech.unifying_receiver import status as _status

_MENU_ICON_SIZE = Gtk.IconSize.LARGE_TOOLBAR

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
	from gi.repository import AppIndicator3 as AppIndicator

	# def _scroll(ind, delta, direction):
	# 	print ("scroll", ind, delta, direction)

	def create(activate_callback, menu_activate_callback):
		assert activate_callback
		assert menu_activate_callback

		ind = AppIndicator.Indicator.new('indicator-solaar', _icons.APP_ICON[0], AppIndicator.IndicatorCategory.HARDWARE)
		ind.set_status(AppIndicator.IndicatorStatus.ACTIVE)

		_create_common(ind, menu_activate_callback)
		ind.set_menu(ind._menu)

		# ind.connect('scroll-event', _scroll)

		return ind


	# def destroy(ind):
	# 	ind.set_status(AppIndicator.IndicatorStatus.PASSIVE)


	def _update_icon(ind, image, tooltip):
		ind.set_icon_full(image, tooltip)


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


	# def destroy(icon):
	# 	icon.set_visible(False)


	def _update_icon(icon, image, tooltip):
		icon.set_from_icon_name(image)
		icon.set_tooltip_markup(tooltip)

#
#
#

def _generate_tooltip_lines(devices_info):
	yield '<b>%s</b>' % NAME
	yield ''

	for _, serial, name, status in devices_info:
		if serial is None:  # receiver
			continue

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

	assert battery_level < 1000
	charging = battery_status.get(_status.BATTERY_CHARGING)
	icon_name = _icons.battery(battery_level, charging)
	if icon_name and 'missing' in icon_name:
		icon_name = None
	return icon_name or _icons.APP_ICON[1]

#
#
#

def _add_device(icon, device):
	index = None
	for idx, (rserial, _, _, _) in enumerate(icon._devices_info):
		if rserial == device.receiver.serial:
			index = idx + 1
			break
	assert index is not None

	device_info = (device.receiver.serial, device.serial, device.name, device.status)
	icon._devices_info.insert(index, device_info)

	menu_item = Gtk.ImageMenuItem.new_with_label('    ' + device.name)
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
	icon_set = _icons.device_icon_set(receiver.name)
	menu_item.set_image(Gtk.Image().new_from_icon_set(icon_set, _MENU_ICON_SIZE))
	menu_item.show_all()
	menu_item.connect('activate', icon._menu_activate_callback, receiver.path, icon)

	icon._devices_info.insert(1, ('-', None, None, None))
	separator = Gtk.SeparatorMenuItem.new()
	separator.set_visible(True)
	icon._menu.insert(separator, 1)

	return 0


def _remove_receiver(icon, receiver):
	index = 0
	found = False
	while index < len(icon._devices_info):
		rserial, _, _, _ = icon._devices_info[index]
		# print ("remove receiver", index, rserial)
		if rserial == receiver.serial:
			found = True
			_remove_device(icon, index)
		elif found and rserial == '-':
			_remove_device(icon, index)
			break
		else:
			index += 1


def _update_menu_item(icon, index, device_status):
	menu_items = icon._menu.get_children()
	menu_item = menu_items[index]

	image = menu_item.get_image()
	level = device_status.get(_status.BATTERY_LEVEL)
	charging = device_status.get(_status.BATTERY_CHARGING)
	image.set_from_icon_name(_icons.battery(level, charging), _MENU_ICON_SIZE)
	image.set_sensitive(bool(device_status))

#
#
#

def update(icon, device=None):
	# print ("icon update", device, icon._devices_info)

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
		no_receivers_index = len(icon._devices_info)
		menu_items[no_receivers_index].set_visible(not icon._devices_info)
		menu_items[no_receivers_index + 1].set_visible(not icon._devices_info)

	tooltip_lines = _generate_tooltip_lines(icon._devices_info)
	tooltip = '\n'.join(tooltip_lines).rstrip('\n')
	_update_icon(icon, _generate_image(icon), tooltip)

	# print ("icon updated", device, icon._devices_info)
