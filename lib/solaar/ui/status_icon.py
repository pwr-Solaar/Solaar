#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger(__name__)
del getLogger

from time import time as _timestamp

from gi.repository import Gtk, GLib
from gi.repository.Gdk import ScrollDirection

from solaar import NAME
from . import action as _action, icons as _icons
from logitech.unifying_receiver import status as _status

_TRAY_ICON_SIZE = 32 #  pixels
_MENU_ICON_SIZE = Gtk.IconSize.LARGE_TOOLBAR

#
#
#

# for which device to show the battery info in systray, if more than one
_picked_device = None



def _create_common(icon, menu_activate_callback):
	icon._devices_info = []

	icon.set_title(NAME)

	icon._menu_activate_callback = menu_activate_callback
	icon._menu = menu = Gtk.Menu()

	# per-device menu entries will be generated as-needed

	no_receiver = Gtk.MenuItem.new_with_label('No receiver found')
	no_receiver.set_sensitive(False)
	menu.append(no_receiver)
	menu.append(Gtk.SeparatorMenuItem.new())

	menu.append(_action.about.create_menu_item())
	menu.append(_action.make('application-exit', 'Quit', Gtk.main_quit).create_menu_item())
	menu.show_all()


try:
	from gi.repository import AppIndicator3

	_log.info("using AppIndicator3")


	_last_scroll = 0
	def _scroll(ind, _, direction):
		if direction != ScrollDirection.UP and direction != ScrollDirection.DOWN:
			# ignore all other directions
			return

		if len(ind._devices_info) < 4:
			# don't bother with scrolling when there's only one receiver
			# with only one device (3 = [receiver, device, separator])
			return

		# scroll events come way too fast (at least 5-6 at once)
		# so take a little break between them
		global _last_scroll
		now = _timestamp()
		if now - _last_scroll < 0.33:  # seconds
			return
		_last_scroll = now

		# if _log.isEnabledFor(_DEBUG):
		# 	_log.debug("scroll direction %s", direction)

		global _picked_device
		candidate = None

		if _picked_device is None:
			for info in ind._devices_info:
				# pick first peripheral found
				if info[1] is not None:
					candidate = info
					break
		else:
			found = False
			for info in ind._devices_info:
				if not info[1]:
					# only conside peripherals
					continue
				# compare peripheral serials
				if info[1] == _picked_device[1]:
					if direction == ScrollDirection.UP and candidate:
						# select previous device
						break
					found = True
				else:
					if found:
						candidate = info
						if direction == ScrollDirection.DOWN:
							break
						# if direction is up, but no candidate found before _picked,
						# let it run through all candidates, will get stuck with the last one
					else:
						if direction == ScrollDirection.DOWN:
							# only use the first one, in case no candidates are after _picked
							if candidate is None:
								candidate = info
						else:
							candidate = info

			# if the last _picked_device is gone, clear it
			# the candidate will be either the first or last one remaining,
			# depending on the scroll direction
			if not found:
				_picked_device = None

		_picked_device = candidate or _picked_device
		if _log.isEnabledFor(_DEBUG):
			_log.debug("scroll: picked %s", _picked_device)
		_update_tray_icon(ind)


	def create(activate_callback, menu_activate_callback):
		assert activate_callback
		assert menu_activate_callback

		theme_paths = Gtk.IconTheme.get_default().get_search_path()

		ind = AppIndicator3.Indicator.new_with_path(
						'indicator-solaar',
						_icons.TRAY_INIT,
						AppIndicator3.IndicatorCategory.HARDWARE,
						':'.join(theme_paths))
		ind.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
		ind.set_attention_icon_full(_icons.TRAY_ATTENTION, '')
		# ind.set_label(NAME, NAME)

		_create_common(ind, menu_activate_callback)
		ind.set_menu(ind._menu)

		ind.connect('scroll-event', _scroll)

		return ind


	def destroy(ind):
		ind.set_status(AppIndicator3.IndicatorStatus.PASSIVE)


	def _update_tray_icon(ind):
		if _picked_device:
			_, _, name, _, device_status = _picked_device
			battery_level = device_status.get(_status.BATTERY_LEVEL)
			battery_charging = device_status.get(_status.BATTERY_CHARGING)
			tray_icon_name = _icons.battery(battery_level, battery_charging)

			description =  '%s: %s' % (name, device_status)
		else:
			# there may be a receiver, but no peripherals
			tray_icon_name = _icons.TRAY_OKAY if ind._devices_info else _icons.TRAY_INIT

			tooltip_lines = _generate_tooltip_lines(ind._devices_info)
			description = '\n'.join(tooltip_lines).rstrip('\n')

		# icon_file = _icons.icon_file(icon_name, _TRAY_ICON_SIZE)
		ind.set_icon_full(tray_icon_name, description)


	def _update_menu_icon(image_widget, icon_name):
		image_widget.set_from_icon_name(icon_name, _MENU_ICON_SIZE)
		# icon_file = _icons.icon_file(icon_name, _MENU_ICON_SIZE)
		# image_widget.set_from_file(icon_file)
		# image_widget.set_pixel_size(_TRAY_ICON_SIZE)


	def attention(ind, reason=None):
		if ind.get_status != AppIndicator3.IndicatorStatus.ATTENTION:
			ind.set_attention_icon_full(_icons.TRAY_ATTENTION, reason or '')
			ind.set_status(AppIndicator3.IndicatorStatus.ATTENTION)
			GLib.timeout_add(10 * 1000, ind.set_status, AppIndicator3.IndicatorStatus.ACTIVE)

except ImportError:

	_log.info("using StatusIcon")

	def create(activate_callback, menu_activate_callback):
		assert activate_callback
		assert menu_activate_callback

		icon = Gtk.StatusIcon.new_from_icon_name(_icons.TRAY_INIT)
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


	def _update_tray_icon(icon):
		tooltip_lines = _generate_tooltip_lines(icon._devices_info)
		tooltip = '\n'.join(tooltip_lines).rstrip('\n')
		icon.set_tooltip_markup(tooltip)

		if _picked_device:
			_, _, name, _, device_status = _picked_device
			battery_level = device_status.get(_status.BATTERY_LEVEL)
			battery_charging = device_status.get(_status.BATTERY_CHARGING)
			tray_icon_name = _icons.battery(battery_level, battery_charging)
		else:
			# there may be a receiver, but no peripherals
			tray_icon_name = _icons.TRAY_OKAY if icon._devices_info else _icons.TRAY_ATTENTION
		icon.set_from_icon_name(tray_icon_name)


	def _update_menu_icon(image_widget, icon_name):
		image_widget.set_from_icon_name(icon_name, _MENU_ICON_SIZE)


	_icon_before_attention = None

	def _blink(icon, count):
		global _icon_before_attention
		if count % 2:
			icon.set_from_icon_name(_icons.TRAY_ATTENTION)
		else:
			icon.set_from_icon_name(_icon_before_attention)

		if count > 0:
			GLib.timeout_add(1000, _blink, icon, count - 1)

	def attention(icon, reason=None):
		global _icon_before_attention
		if _icon_before_attention is None:
			_icon_before_attention = icon.get_icon_name()
			GLib.idle_add(_blink, icon, 9)

#
#
#

def _generate_tooltip_lines(devices_info):
	if not devices_info:
		yield '<b>%s</b>: no receivers' % NAME
		return

	yield '<b>%s</b>' % NAME
	yield ''

	for _, serial, name, _, status in devices_info:
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


def _pick_device_with_lowest_battery(devices_info):
	if not devices_info:
		return None

	picked = None
	picked_level = 1000

	for info in devices_info:
		if info[1] is None: # is receiver/separator
			continue
		level = info[-1].get(_status.BATTERY_LEVEL)
		if not picked or (level is not None and picked_level > level):
			picked = info
			picked_level = level or 0

	if _log.isEnabledFor(_DEBUG):
		_log.debug("picked device with lowest battery: %s", picked)

	return picked


#
#
#

def _add_device(icon, device):
	index = None
	for idx, (rserial, _, _, _, _) in enumerate(icon._devices_info):
		if rserial == device.receiver.serial:
			# the first entry matching the receiver serial should be for the receiver itself
			index = idx + 1
			break
	assert index is not None

	# proper ordering (according to device.number) for a receiver's devices
	while True:
		rserial, _, _, number, _ = icon._devices_info[index]
		if rserial == '-':
			break
		assert rserial == device.receiver.serial
		assert number != device.number
		if number > device.number:
			break
		index = index + 1

	device_info = (device.receiver.serial, device.serial, device.name, device.number, device.status)
	icon._devices_info.insert(index, device_info)

	# print ("status_icon: added", index, ":", device_info)

	# label_prefix = b'\xE2\x94\x84 '.decode('utf-8')
	label_prefix = '   '

	menu_item = Gtk.ImageMenuItem.new_with_label(label_prefix + device.name)
	menu_item.set_image(Gtk.Image())
	menu_item.show_all()
	menu_item.connect('activate', icon._menu_activate_callback, device.receiver.path, icon)

	icon._menu.insert(menu_item, index)

	return index


def _remove_device(icon, index):
	assert index is not None

	menu_items = icon._menu.get_children()
	icon._menu.remove(menu_items[index])

	removed_device = icon._devices_info.pop(index)
	global _picked_device
	if _picked_device and _picked_device[1] == removed_device[1]:
		# the current pick was unpaired
		_picked_device = None


def _add_receiver(icon, receiver):
	device_info = (receiver.serial, None, receiver.name, None, None)
	icon._devices_info.insert(0, device_info)

	menu_item = Gtk.ImageMenuItem.new_with_label(receiver.name)
	icon._menu.insert(menu_item, 0)
	icon_set = _icons.device_icon_set(receiver.name)
	menu_item.set_image(Gtk.Image().new_from_icon_set(icon_set, _MENU_ICON_SIZE))
	menu_item.show_all()
	menu_item.connect('activate', icon._menu_activate_callback, receiver.path, icon)

	icon._devices_info.insert(1, ('-', None, None, None, None))
	separator = Gtk.SeparatorMenuItem.new()
	separator.set_visible(True)
	icon._menu.insert(separator, 1)

	return 0


def _remove_receiver(icon, receiver):
	index = 0
	found = False

	# remove all entries in devices_info that match this receiver
	while index < len(icon._devices_info):
		rserial, _, _, _, _ = icon._devices_info[index]
		if rserial == receiver.serial:
			found = True
			_remove_device(icon, index)
		elif found and rserial == '-':
			# the separator after this receiver
			_remove_device(icon, index)
			break
		else:
			index += 1


def _update_menu_item(icon, index, device_status):
	menu_items = icon._menu.get_children()
	menu_item = menu_items[index]

	level = device_status.get(_status.BATTERY_LEVEL)
	charging = device_status.get(_status.BATTERY_CHARGING)
	icon_name = _icons.battery(level, charging)

	image_widget = menu_item.get_image()
	image_widget.set_sensitive(bool(device_status))
	_update_menu_icon(image_widget, icon_name)

#
#
#

def update(icon, device=None):
	if device is not None:
		if device.kind is None:
			# receiver
			receiver = device
			if receiver:
				index = None
				for idx, (rserial, _, _, _, _) in enumerate(icon._devices_info):
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
			for idx, (rserial, serial, name, _, _) in enumerate(icon._devices_info):
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

	global _picked_device
	if not _picked_device:
		_picked_device = _pick_device_with_lowest_battery(icon._devices_info)

	_update_tray_icon(icon)
