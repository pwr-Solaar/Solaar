#!/usr/bin/env python

import logging
logging.basicConfig(level=1)
logging.captureWarnings(True)

import time
import threading
import subprocess
from collections import namedtuple

from gi.repository import GObject
from gi.repository import Gtk

from logitech.unifying_receiver import api as ur


#
# A few constants
#

KEYBOARD_NAME = 'Wireless Solar Keyboard K750'
TITLE = 'Solar [K750]'

NOTIFY_DESKTOP = True

OK = 0
NO_RECEIVER = 1
NO_K750 = 2
NO_STATUS = 3

SLEEP = (10, 5, 5, 15)
TEXT = ('K750 keyboard connected',
		'Logitech Unifying Receiver not detected',
		'K750 keyboard not detected',
		'K750 keyboard not responding')
# ICON_NAMES = (
# 				'status_good', 'status_attention',
# 				'status_attention', 'status_warning'
# 			)
CHARGE_LUX_TEXT = 'Charge: %d%%    Lux: %d'


K750_Status = namedtuple('K750_Status',
						['receiver', 'device', 'status', 'charge', 'lux'])


#
#
#


# _unhandled_queue = []

# def unhandled_messages_hook(code, device, data):
# 	if len(_unhandled_queue) > 32:
# 		del _unhandled_queue[:]
# 	_unhandled_queue.append((code, device, data))

# from logitech.unifying_receiver import unhandled
# unhandled.set_unhandled_hook(unhandled_messages_hook)


#
#
#


def notify_desktop(status_code, text):
	global NOTIFY_DESKTOP
	if NOTIFY_DESKTOP:
		try:
			subprocess.call(('notify-send', '-u', 'low', TITLE, text))
		except OSError:
			NOTIFY_DESKTOP = False


def update_status_icon(status_icon, status_changed, k750):
	print "update status", status_changed, k750

	text = TEXT[k750.status]
	if k750.status == OK:
		text += '\n' + (CHARGE_LUX_TEXT % (k750.charge, k750.lux))
	# print text
	status_icon.set_tooltip_text(text)

	if status_changed:
		notify_desktop(k750.status, text)


def read_charge(receiver, device):
	status, charge, lux = NO_RECEIVER, -1, -1

	if receiver is None:
		receiver = ur.open()
		device = None

	if receiver and not device:
		try:
			device = ur.find_device_by_name(receiver, KEYBOARD_NAME)
		except ur.NoReceiver:
			receiver = None

	if receiver and device:
		feature_solar_index = device.features_array.index(ur.FEATURE.SOLAR_CHARGE)

		event = None
		for i in range(0, 20):
			next_event = ur.base.read(receiver, ur.base.DEFAULT_TIMEOUT * 2 // i if i > 0 else ur.base.DEFAULT_TIMEOUT * 3)
			if not next_event:
				break
			if next_event[1] == device.number:
				if next_event[0] == 0x10 and next_event[2][0] == b'\x8F':
					event = next_event
				elif next_event[0] == 0x11 and next_event[2][0] == chr(feature_solar_index) and next_event[2][7:11] == b'GOOD':
					if next_event[2][1] == b'\x10':
						event = next_event
					elif next_event[2][1] == b'\x00' or next_event[2][1] == b'\x20':
						event = next_event

		if event is None:
			try:
				reply = ur.request(receiver, device.number, ur.FEATURE.SOLAR_CHARGE, function=b'\x03', params=b'\x78\x01', features_array=device.features_array)
				if reply is None:
					status = NO_K750
					device = None
				else:
					return read_charge(receiver, device)
			except ur.NoReceiver:
				receiver = None
				device = None
		else:
			if event[1] == 0x10:
				status = NO_K750
				device = None
			else:
				status = OK
				charge = ord(event[2][2])
				if event[2][1] == b'\x10':
					lux = (ord(event[2][3]) << 8) + ord(event[2][4])

	return K750_Status(receiver, device, status, charge, lux)


class StatusThread(threading.Thread):
	def __init__(self, status_icon):
		super(StatusThread, self).__init__()
		self.daemon = True
		self.status_icon = status_icon

	def run(self):
		last_status = NO_RECEIVER
		k750 = K750_Status(None, None, NO_RECEIVER, 0, 0)

		while True:
			k750 = read_charge(k750.receiver, k750.device)
			status_changed = k750.status != last_status
			GObject.idle_add(update_status_icon, self.status_icon, status_changed, k750)
			last_status = k750.status
			time.sleep(SLEEP[k750.status])


if __name__ == "__main__":
	status_icon = Gtk.StatusIcon.new_from_file('images/icon.png')
	status_icon.set_title(TITLE)
	status_icon.set_name(TITLE)
	status_icon.set_tooltip_text('Initializing...')
	status_icon.connect("popup_menu", Gtk.main_quit)

	GObject.threads_init()
	StatusThread(status_icon).start()
	Gtk.main()
