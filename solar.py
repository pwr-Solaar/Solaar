import time
import threading
import subprocess
from collections import namedtuple

import gobject
import pygtk
pygtk.require('2.0')
import gtk

from logitech import unifying_receiver as ur


KEYBOARD_NAME = 'Wireless Solar Keyboard K750'
TITLE = 'Solar [K750]'

NOTIFY_DESKTOP = True
BLINK_ICON = 3

OK = 0
NO_RECEIVER = 1
NO_K750 = 2
NO_STATUS = 3

SLEEP = (10, 30, 25, 15)
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


def notify_desktop(status_code, text):
	global NOTIFY_DESKTOP
	if NOTIFY_DESKTOP:
		try:
			program = ('/usr/bin/notify-send', '-u', 'low', TITLE, text)
			subprocess.Popen(program, close_fds=True)
		except OSError:
			NOTIFY_DESKTOP = False


def update_status_icon(status_icon, status_changed, k750):
	text = TEXT[k750.status]
	if k750.status == OK:
		text += '\n' + (CHARGE_LUX_TEXT % (k750.charge, k750.lux))
	# print text
	status_icon.set_tooltip_text(text)

	if status_changed:
		notify_desktop(k750.status, text)
		if BLINK_ICON:
			status_icon.set_blinking(True)
			time.sleep(BLINK_ICON)
			status_icon.set_blinking(False)


def read_charge(receiver, device):
	status, charge, lux = NO_RECEIVER, -1, -1

	if receiver is None:
		receiver = ur.open()
		device = None

	if receiver and not device:
		try:
			device = ur.find_device(receiver, "keyboard", KEYBOARD_NAME)
		except ur.NoReceiver:
			ur.close(receiver)
			receiver = None

	if receiver:
		if device:
			try:
				charge_lux = ur.get_solar_charge(receiver, device)
				if charge_lux is None:
					device = None
					status = NO_STATUS
				else:
					charge, lux = charge_lux
					status = OK
			except ur.NoReceiver:
				ur.close(receiver)
				receiver = None
		else:
			status = NO_K750

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
			gobject.idle_add(update_status_icon, self.status_icon, status_changed, k750)
			last_status = k750.status
			time.sleep(SLEEP[k750.status])


if __name__ == "__main__":
	status_icon = gtk.status_icon_new_from_file('images/icon.png')
	status_icon.set_title('Solar')
	status_icon.set_tooltip_text('Initializing...')
	status_icon.connect("popup_menu", gtk.main_quit)

	gobject.threads_init()
	StatusThread(status_icon).start()
	gtk.main()
