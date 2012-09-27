#!/usr/bin/env python

import logging
import time
import threading

from gi.repository import GObject
from gi.repository import Gtk

from logitech.unifying_receiver import api as ur
from logitech.unifying_receiver.listener import EventsListener

from logitech.devices import *


#
# A few constants
#

APP_TITLE = 'Solaar'
UNIFYING_RECEIVER = 'Unifying Receiver'
NO_DEVICES = 'No devices attached.'
NO_RECEIVER = 'Unifying Receiver not found.'
FOUND_RECEIVER = 'Unifying Receiver detected.'

STATUS_TIMEOUT = 31  # seconds
ICON_UPDATE_SLEEP = 7  # seconds


#
#
#


try:
	import notify2
	notify2.init(APP_TITLE)

	_notifications = {}
	import os.path
	_ICONS = {}

	def notify_desktop(status, title, text, icon=None):
		def _icon_path(name):
			path = os.path.join(__file__, '..', 'images', name + '.png')
			path = os.path.normpath(path)
			path = os.path.abspath(path)
			return path if os.path.isfile(path) else None

		if icon is None:
			icon = title
		if icon not in _ICONS:
			_ICONS[icon] = _icon_path(icon)
		icon_path = _ICONS[icon]
		if icon_path:
			icon = icon_path
		if icon is None:
			icon = 'error' if status < 0 else 'info'

		if title in _notifications:
			notification = _notifications[title]
		else:
			notification = notify2.Notification(title, icon=icon)
			notification.set_category(APP_TITLE)
			_notifications[title] = notification

		notification.set_urgency(notify2.URGENCY_CRITICAL if status < 0 else notify2.URGENCY_NORMAL)
		notification.update(title, text, icon)
		notification.show()
except ImportError:
	def notify_desktop(status, title, text, icon=None):
		pass


#
#
#


class StatusThread(threading.Thread):
	def __init__(self, status_icon):
		super(StatusThread, self).__init__(name='StatusThread')
		self.daemon = True
		self.status_icon = status_icon

		self.last_receiver_status = None
		self.listener = None
		self.devices = {}
		self.statuses = {}

	def run(self):
		self.active = True
		while self.active:
			if self.listener is None:
				receiver = ur.open()
				if receiver:
					for devinfo in ur.list_devices(receiver):
						self.devices[devinfo.number] = devinfo
					self.listener = EventsListener(receiver, self.events_callback)
					logging.info("started events listener %s", self.listener)
					self.listener.start()
					notify_desktop(1, UNIFYING_RECEIVER, FOUND_RECEIVER)
					self.last_receiver_status = 1
				else:
					if self.last_receiver_status != -1:
						notify_desktop(-1, UNIFYING_RECEIVER, NO_RECEIVER)
						self.last_receiver_status = -1
			elif not self.listener.active:
				logging.info("events listener %s stopped", self.listener)
				self.listener = None
				self.devices.clear()
				self.statuses.clear()
				notify_desktop(-1, UNIFYING_RECEIVER, NO_RECEIVER)
				self.last_receiver_status = -1

			if self.active:
				update_icon = True
				if self.listener and self.devices:
					update_icon &= self.update_old_statuses()

			if self.active and update_icon:
				GObject.idle_add(self.update_status_icon)

			if self.active:
				time.sleep(ICON_UPDATE_SLEEP)

	def stop(self):
		self.active = False
		if self.listener:
			self.listener.stop()
			ur.close(self.listener.receiver)

	def update_old_statuses(self):
		updated = False

		for devinfo in self.devices.values():
			if devinfo.number not in self.statuses:
				self.statuses[devinfo.number] = [0, None, None]

			last_status_time = self.statuses[devinfo.number][0]
			if time.time() - last_status_time > STATUS_TIMEOUT:
				status = request_status(devinfo, self.listener)
				updated |= self.device_status_changed(devinfo, status)

		return updated

	def events_callback(self, code, device, data):
		updated = False

		if device in self.devices:
			devinfo = self.devices[device]
			if code == 0x10 and data[0] == 'b\x8F':
				updated = True
				self.device_status_changed(devinfo, DEVICE_STATUS.UNAVAILABLE)
			elif code == 0x11:
				status = process_event(devinfo, self.listener, data)
				updated |= self.device_status_changed(devinfo, status)
			else:
				logging.warn("unknown event code %02x", code)
		elif device:
			logging.debug("got event (%d, %d, %s) for new device", code, device, data.encode('hex'))
			devinfo = ur.get_device_info(self.listener.receiver, device)
			if devinfo:
				self.devices[device] = devinfo
				self.statuses[device] = [0, None, None]
			else:
				logging.warn("got event (%d, %d, %s) for unknown device", code, device, data.encode('hex'))
		else:
			logging.warn("don't know how to handle event (%d, %d, %s)", code, device, data.encode('hex'))

		if updated:
			GObject.idle_add(self.update_status_icon)

	def device_status_changed(self, devinfo, status):
		if status is None or devinfo.number not in self.statuses:
			return False

		if type(status) == int:
			status_code = status
			status_text = DEVICE_STATUS_NAME[status_code]
		else:
			status_code = status[0]
			status_text = DEVICE_STATUS_NAME[status_code] if status[1] is None else status[1]

		device_status = self.statuses[devinfo.number]
		old_status_code = device_status[1]

		device_status[0] = time.time()
		device_status[1] = status_code
		device_status[2] = status_text

		if old_status_code != status_code:
			logging.debug("device status changed from %s => %s: %s", old_status_code, status_code, status_text)
			notify_desktop(status_code, devinfo.name, status_text)

		return True

	def update_status_icon(self):
		if self.listener:
			all_statuses = []
			for d in self.devices:
				devinfo = self.devices[d]
				status_text = self.statuses[d][2]
				if status_text:
					all_statuses.append(unichr(0x274a) + ' ' + devinfo.name + '\n\t' + status_text)
				else:
					all_statuses.append(devinfo.name)

			if all_statuses:
				tooltip = '\n'.join(all_statuses)
			else:
				tooltip = NO_DEVICES
		else:
			tooltip = NO_RECEIVER

		# logging.debug("tooltip %s", tooltip)
		self.status_icon.set_tooltip_text(tooltip)


if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG)
	logging.captureWarnings(True)

	status_icon = Gtk.StatusIcon.new_from_file('images/' + UNIFYING_RECEIVER + '.png')
	status_icon.set_title(APP_TITLE)
	status_icon.set_name(APP_TITLE)
	status_icon.set_tooltip_text('Initializing...')
	status_icon.connect('popup_menu', Gtk.main_quit)

	GObject.threads_init()
	status_thread = StatusThread(status_icon)
	status_thread.start()
	Gtk.main()
	status_thread.stop()
