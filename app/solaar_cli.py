#!/usr/bin/env python -u

from __future__ import absolute_import, division, print_function, unicode_literals

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

#
#
#

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
		_fail("need at least 3 characters to match a device")

	name = name.lower()
	if 'receiver'.startswith(name) or name == receiver.serial:
		return receiver

	dev = None
	for d in receiver:
		if name == d.serial or name in d.name.lower() or name in d.codename.lower():
			if dev is None:
				dev = d
			else:
				_fail("'%s' matches multiple devices" % name)

	if dev is None:
		_fail("no device found matching '%s'" % name)
	return dev


def _print_receiver(receiver, verbose=False):
	if not verbose:
		print ("-: Unifying Receiver [%s:%s] with %d devices" % (receiver.path, receiver.serial, receiver.count()))
		return

	print ("-: Unifying Receiver")
	print ("   Device path  : %s" % receiver.path)
	print ("   Serial       : %s" % receiver.serial)
	for f in receiver.firmware:
		print ("     %-11s: %s" % (f.kind, f.version))

	print ("   Has %d paired device(s)." % receiver.count())

	notifications = receiver.request(0x8100)
	if notifications:
		notifications = ord(notifications[0:1]) << 16 | ord(notifications[1:2]) << 8
		if notifications:
			from logitech.unifying_receiver import hidpp10
			print ("   Enabled notifications: %s." % hidpp10.NOTIFICATION_FLAG.flag_names(notifications))
		else:
			print ("   All notifications disabled.")

	activity = receiver.request(0x83B3)
	if activity:
		activity = [(d, ord(activity[d - 1:d])) for d in range(1, receiver.max_devices)]
		print("   Device activity counters: %s" % ', '.join(('%d=%d' % (d, a)) for d, a in activity if a > 0))


def _print_device(dev, verbose=False):
	p = dev.protocol
	state = '' if p > 0 else ' inactive'

	if not verbose:
		print ("%d: %s [%s:%s]%s" % (dev.number, dev.name, dev.codename, dev.serial, state))
		return

	print ("%d: %s" % (dev.number, dev.name))
	print ("   Codename     : %s" % dev.codename)
	print ("   Kind         : %s" % dev.kind)
	if p == 0:
		print ("   Protocol     : unknown (device is inactive)")
	else:
		print ("   Protocol     : HID++ %1.1f" % p)
	print ("   Polling rate : %d ms" % dev.polling_rate)
	print ("   Wireless PID : %s" % dev.wpid)
	print ("   Serial number: %s" % dev.serial)
	for fw in dev.firmware:
		print ("     %-11s: %s" % (fw.kind, (fw.name + ' ' + fw.version).strip()))

	if dev.power_switch_location:
		print ("   The power switch is located on the %s" % dev.power_switch_location)

	from logitech.unifying_receiver import hidpp10, hidpp20
	if p > 0:

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
				print ("      %2d: %-20s => %-20s   %s" % (k.index, k.key, k.task, flags))

	if p > 0:
		battery = hidpp20.get_battery(dev)
		if battery is None:
			battery = hidpp10.get_battery(dev)
		if battery:
			charge, status = battery
			print ("   Battery is %d%% charged, %s" % (charge, status))
		else:
			print ("   Battery status unavailable.")
	else:
		print ("   Battery status is unknown (device is inactive).")

#
#
#

def show_devices(receiver, args):
	if args.device == 'all':
		_print_receiver(receiver, args.verbose)
		for dev in receiver:
			if args.verbose:
				print ("")
			_print_device(dev, args.verbose)
	else:
		dev = _find_device(receiver, args.device)
		if dev is receiver:
			_print_receiver(receiver, args.verbose)
		else:
			_print_device(dev, args.verbose)


def pair_device(receiver, args):
	# get all current devices
	known_devices = [dev.number for dev in receiver]

	from logitech.unifying_receiver import status
	r_status = status.ReceiverStatus(receiver, lambda *args, **kwargs: None)

	done = [False]

	def _events_handler(event):
		if event.devnumber == 0xFF:
			r_status.process_event(event)
			if not r_status.lock_open:
				done[0] = True
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

	while not done[0]:
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
		_fail("cannot unpair the receiver from itself!")

	# query these now, it's last chance to get them
	number, name, codename, serial = dev.number, dev.name, dev.codename, dev.serial
	try:
		del receiver[number]
		print ("Unpaired %d: %s [%s:%s]" % (number, name, codename, serial))
	except Exception as e:
		_fail("failed to unpair device %s: %s" % (dev.name, e))


def config_device(receiver, args):
	dev = _find_device(receiver, args.device)
	if dev is receiver:
		_fail("no settings for the receiver")

	if not dev.settings:
		_fail("no settings for %s" % dev.name)

	if not args.setting:
		print ("[%d:%s:%s]" % (dev.number, dev.name, dev.serial))
		for s in dev.settings:
			print ("")
			print ("# %s" % s.label)
			if s.choices:
				print ("#   possible values: [%s]" % ', '.join(str(v) for v in s.choices))
			value = s.read()
			if value is None:
				print ("#   !! failed to read '%s'" % s.name)
			else:
				print ("%s=%s" % (s.name, value))
		return

	setting = None
	for s in dev.settings:
		if args.setting.lower() == s.name.lower():
			setting = s
			break
	if setting is None:
		_fail("no setting '%s' for %s" % (args.setting, dev.name))

	if args.value is None:
		result = setting.read()
		if result is None:
			_fail("failed to read '%s'" % setting.name)
		print ("%s = %s" % (setting.name, setting.read()))
		return

	from logitech.unifying_receiver import settings as _settings

	if setting.kind == _settings.KIND.toggle:
		value = args.value
		try:
			value = bool(int(value))
		except:
			if value.lower() in ['1', 'true', 'yes', 't', 'y']:
				value = True
			elif value.lower() in ['0', 'false', 'no', 'f', 'n']:
				value = False
			else:
				_fail("don't know how to interpret '%s' as boolean" % value)
	elif setting.choices:
		value = args.value.lower()
		if value not in setting.choices:
			_fail("possible values for '%s' are: [%s]" % (setting.name, ', '.join(str(v) for v in setting.choices)))
		value = setting.choices[setting.choices.index(value)]
	else:
		raise NotImplemented

	result = setting.write(value)
	if result is None:
		_fail("failed to set '%s' to '%s'" % (setting.name, value))
	print ("%s = %s" % (setting.name, result))

#
#
#

def _parse_arguments():
	import argparse
	arg_parser = argparse.ArgumentParser(prog=NAME.lower())
	arg_parser.add_argument('-d', '--debug', action='count', default=0,
							help='print logging messages, for debugging purposes (may be repeated for extra verbosity)')
	arg_parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__)

	subparsers = arg_parser.add_subparsers(title='commands')

	sp = subparsers.add_parser('show', help='show information about paired devices')
	sp.add_argument('device', nargs='?', default='all',
					help='device to show information about; may be a device number (1..6), a device serial, '
						'at least 3 characters of a device\'s name, "receiver", or "all" (the default)')
	sp.add_argument('-v', '--verbose', action='store_true',
					help='print all available information about the inspected device(s)')
	sp.set_defaults(cmd=show_devices)

	sp = subparsers.add_parser('config', help='read/write device-specific settings',
								epilog='Please note that configuration only works on active devices.')
	sp.add_argument('device',
					help='device to configure; may be a device number (1..6), a device serial, '
							'or at least 3 characters of a device\'s name')
	sp.add_argument('setting', nargs='?',
					help='device-specific setting; leave empty to list available settings')
	sp.add_argument('value', nargs='?',
					help='new value for the setting')
	sp.set_defaults(cmd=config_device)

	sp = subparsers.add_parser('pair', help='pair a new device',
								epilog='The Logitech Unifying Receiver supports up to 6 paired devices at the same time.')
	sp.set_defaults(cmd=pair_device)

	sp = subparsers.add_parser('unpair', help='unpair a device')
	sp.add_argument('device',
					help='device to unpair; may be a device number (1..6), a device serial, '
						'or at least 3 characters of a device\'s name.')
	sp.set_defaults(cmd=unpair_device)

	args = arg_parser.parse_args()

	import logging
	if args.debug > 0:
		log_level = logging.WARNING - 10 * args.debug
		log_format='%(asctime)s %(levelname)8s %(name)s: %(message)s'
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
