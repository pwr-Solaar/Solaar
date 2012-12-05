#!/usr/bin/env python -u

import sys

import solaar
NAME = 'solaar-cli'
__author__  = solaar.__author__
__version__ = solaar.__version__
__license__ = solaar.__license__

#
#
#


def _fail(text):
	sys.exit("%s: error: %s" % (NAME, text))


def _require(module, os_package):
	try:
		__import__(module)
	except ImportError:
		_fail("missing required package '%s'" % os_package)


def _receiver():
	from logitech.unifying_receiver import Receiver
	try:
		r = Receiver.open()
	except Exception as e:
		_fail(str(e))
	if r is None:
		_fail("Logitech Unifying Receiver not found")
	return r


def _find_device(receiver, name):
	if len(name) == 1:
		try:
			number = int(name)
		except:
			pass
		else:
			if number in range(1, 1 + receiver.max_devices):
				dev = receiver[number]
				if dev is None:
					_fail("no paired device with number %d" % number)
				return dev

	if len(name) < 3:
		_fail("need at least 3 characters to match the device")

	if name in 'receiver':
		return receiver

	dev = None
	for d in receiver:
		if name in d.name.lower() or name in d.codename.lower():
			if dev is None:
				dev = d
			else:
				_fail("'%s' matches multiple devices" % name)

	if dev is None:
		_fail("no device found matching '%s'" % name)
	return dev


def _print_receiver(receiver, short=True):
	if short:
		print ("-: Unifying Receiver [%s:%s]" % (receiver.path, receiver.serial))
		return

	print ("-: Unifying Receiver")
	print ("   Device path  : %s" % receiver.path)
	print ("   Serial       : %s" % receiver.serial)
	for f in receiver.firmware:
		print ("     %-11s: %s" % (f.kind, f.version))

	notifications = receiver.request(0x8100)
	if notifications:
		notifications = ord(notifications[0:1]) << 16 | ord(notifications[1:2]) << 8
		if notifications:
			from logitech.unifying_receiver import hidpp10
			print ("   Enabled notifications: %s." % hidpp10.NOTIFICATION_FLAG.flag_names(notifications))
		else:
			print ("   All notifications disabled.")

	print ("   Reported %d paired device(s)." % receiver.count())
	activity = receiver.request(0x83B3)
	if activity:
		activity = [(d, ord(activity[d - 1:d])) for d in range(1, receiver.max_devices)]
		print("   Device activity counters: %s" % ', '.join(('%d=%d' % (d, a)) for d, a in activity if a > 0))


def _print_device(dev, short=True):
	p = dev.protocol
	state = '' if p > 0 else ' inactive'

	if short:
		print ("%d: %s [%s:%s]%s" % (dev.number, dev.name, dev.codename, dev.serial, state))
		return

	print ("%d: %s" % (dev.number, dev.name))
	print ("   Codename     : %s" % dev.codename)
	print ("   Kind         : %s" % dev.kind)
	print ("   Serial number: %s" % dev.serial)
	print ("   Wireless PID : %s" % dev.wpid)

	if p == 0:
		print ("   Protocol     : unknown (device is inactive)")
	else:
		print ("   Protocol     : HID++ %1.1f" % p)

	for fw in dev.firmware:
		print ("     %-11s: %s %s" % (fw.kind, fw.name, fw.version))

	if dev.power_switch_location:
		print ("   The power switch is located on the %s" % dev.power_switch_location)
	if p == 0:
		return

	from logitech.unifying_receiver import hidpp10, hidpp20

	if dev.features:
		print ("   Supports %d HID++ 2.0 features:" % len(dev.features))
		for index, feature in enumerate(dev.features):
			feature = dev.features[index]
			flags = dev.request(0x0000, feature.bytes(2))
			flags = 0 if flags is None else ord(flags[1:2])
			flags = hidpp20.FEATURE_FLAG.flag_names(flags)
			print ("      %2d: %-20s {%04X}   %s" % (index, feature, feature, flags))

	if dev.keys:
		print ("   Has %d reprogrammable keys:" % len(dev.keys))
		for k in dev.keys:
			flags = hidpp20.KEY_FLAG.flag_names(k.flags)
			print ("      %2d: %-20s => %-20s   %s" % (k.index, hidpp20.KEY[k.key], hidpp20.KEY[k.task], flags))

	battery = hidpp10.get_battery(dev) or hidpp20.get_battery(dev)
	if battery:
		charge, status = battery
		print ("   Battery: %d%% charged, %s" % (charge, status))
	else:
		print ("   Battery report not supported.")


def list_devices(receiver, args):
	_print_receiver(receiver, args.short)
	for dev in receiver:
		if not args.short:
			print ("")
		_print_device(dev, args.short)


def show_device(receiver, args):
	dev = _find_device(receiver, args.device)
	if dev is receiver:
		_print_receiver(receiver, False)
	else:
		_print_device(dev, False)


def pair_device(receiver, args):
	# get all current devices
	known_devices = [dev.number for dev in receiver]

	from threading import Event
	done = Event()

	from logitech.unifying_receiver import status
	r_status = status.ReceiverStatus(receiver, lambda *args, **kwargs: None)

	def _events_handler(event):
		if event.devnumber == 0xFF:
			r_status.process_event(event)
			if not r_status.lock_open:
				done.set()
		elif event.sub_id == 0x41 and event.address == 0x04:
			if event.devnumber not in known_devices:
				r_status.new_device = receiver[event.devnumber]

	from logitech.unifying_receiver import base
	base.events_hook = _events_handler

	# check if it's necessary to set the notification flags
	notifications = receiver.request(0x8100)
	if notifications:
		notifications = ord(notifications[:1]) + ord(notifications[1:2]) + ord(notifications[2:3])
	if not notifications:
		receiver.enable_notifications()
	receiver.set_lock(False, timeout=20)
	print ("Pairing: turn your new device on (timing out in 20 seconds).")

	while not done.is_set():
		event = base.read(receiver.handle, 2000)
		if event:
			event = base.make_event(*event)
			if event:
				_events_handler(event)

	if not notifications:
		receiver.enable_notifications(False)
	base.events_hook = None

	if r_status.new_device:
		dev = r_status.new_device
		print ("Paired device %d: %s [%s:%s]" % (dev.number, dev.name, dev.codename, dev.serial))
	else:
		_fail(r_status[status.ERROR])


def unpair_device(receiver, args):
	dev = _find_device(receiver, args.device)
	if dev is receiver:
		_fail("cannot unpair the receiver")

	# query these
	number, name, codename, serial = dev.number, dev.name, dev.codename, dev.serial
	try:
		del receiver[number]
		print ("Unpaired %d: %s [%s:%s]" % (number, name, codename, serial))
	except Exception as e:
		_fail("failed to unpair device %s: %s" % (dev.name, e))


def _parse_arguments():
	import argparse
	arg_parser = argparse.ArgumentParser(prog=NAME.lower())
	arg_parser.add_argument('-v', '--verbose',
							action='count', default=0,
							help='increase the logger verbosity (may be repeated)')
	arg_parser.add_argument('-V', '--version',
							action='version',
							version='%(prog)s ' + __version__)
	subparsers = arg_parser.add_subparsers(title='sub-commands')

	list_p = subparsers.add_parser('list', help='list paired devices')
	list_p.add_argument('--full', action='store_false', dest='short',
						help='print full info about each device')
	list_p.set_defaults(cmd=list_devices)

	show_p = subparsers.add_parser('show', help='show info about a single device',
					epilog='The <device> argument may be a device number (1..6),'
							' at least 3 characters of a device\'s name,'
							' or "receiver".')
	show_p.add_argument('device', help='device to show information about')
	show_p.set_defaults(cmd=show_device)

	pair_p = subparsers.add_parser('pair', help='pair a new device')
	pair_p.set_defaults(cmd=pair_device)

	unpair_p = subparsers.add_parser('unpair', help='unpair a device',
					epilog='The <device> argument may be a device number (1..6),'
							' or at least 3 characters of a device\'s name.')
	unpair_p.add_argument('device', help='device to unpair')
	unpair_p.set_defaults(cmd=unpair_device)

	args = arg_parser.parse_args()

	import logging
	if args.verbose > 0:
		log_level = logging.WARNING - 10 * args.verbose
		log_format='%(asctime)s %(levelname)8s [%(threadName)s] %(name)s: %(message)s'
		logging.basicConfig(level=max(log_level, logging.DEBUG), format=log_format)
	else:
		logging.root.addHandler(logging.NullHandler())
		logging.root.setLevel(logging.CRITICAL)

	return args


if __name__ == '__main__':
	_require('pyudev', 'python-pyudev')
	args = _parse_arguments()
	receiver = _receiver()
	args.cmd(receiver, args)
