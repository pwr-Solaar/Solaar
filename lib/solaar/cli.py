#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import logging


NAME = 'solaar-cli'
from solaar import __version__

#
#
#

def _fail(text):
	if sys.exc_info()[0]:
		logging.exception(text)
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
	from logitech.unifying_receiver.base import receivers
	for dev_info in receivers():
		try:
			r = Receiver.open(dev_info)
			if r:
				return r
		except Exception as e:
			_fail(str(e))
		return r
	_fail("Logitech receiver not found")


def _find_device(receiver, name, may_be_receiver=False):
	if len(name) == 1:
		try:
			number = int(name)
		except:
			pass
		else:
			if number in range(1, 1 + receiver.max_devices):
				dev = receiver[number]
				if dev is None:
					_fail("no paired device with number", number)
				return dev

	if len(name) < 3:
		_fail("need at least 3 characters to match a device")

	name = name.lower()
	if may_be_receiver and ('receiver'.startswith(name) or name == receiver.serial.lower()):
		return receiver

	for dev in receiver:
		if (name == dev.serial.lower() or
			name == dev.codename.lower() or
			name == str(dev.kind).lower() or
			name in dev.name.lower()):
			return dev

	_fail("no device found matching '%s'" % name)


def _print_receiver(receiver, verbose=False):
	paired_count = receiver.count()
	if not verbose:
		print ("-: Unifying Receiver [%s:%s] with %d devices" % (receiver.path, receiver.serial, paired_count))
		return

	print ("-: Unifying Receiver")
	print ("   Device path  :", receiver.path)
	print ("   Serial       :", receiver.serial)
	for f in receiver.firmware:
		print ("     %-11s: %s" % (f.kind, f.version))

	print ("   Has", paired_count, "paired device(s) out of a maximum of", receiver.max_devices)

	notification_flags = receiver.request(0x8100)
	if notification_flags:
		notification_flags = ord(notification_flags[0:1]) << 16 | ord(notification_flags[1:2]) << 8
		if notification_flags:
			from logitech.unifying_receiver import hidpp10
			notification_names = hidpp10.NOTIFICATION_FLAG.flag_names(notification_flags)
			print ("   Enabled notifications: 0x%06X = %s." % (notification_flags, ', '.join(notification_names)))
		else:
			print ("   All notifications disabled")

	if receiver.unifying_supported:
		activity = receiver.request(0x83B3)
		if activity:
			activity = [(d, ord(activity[d - 1:d])) for d in range(1, receiver.max_devices)]
			print ("   Device activity counters:", ', '.join(('%d=%d' % (d, a)) for d, a in activity if a > 0))


def _print_device(dev, verbose=False):
	p = dev.protocol
	state = '' if p > 0 else 'inactive'

	if not verbose:
		print ("%d: %s [%s:%s]" % (dev.number, dev.name, dev.codename, dev.serial), state)
		return

	print ("%d: %s" % (dev.number, dev.name))
	print ("   Codename     :", dev.codename)
	print ("   Kind         :", dev.kind)
	if p == 0:
		print ("   Protocol     : unknown (device is inactive)")
	else:
		print ("   Protocol     : HID++ %1.1f" % p)
	print ("   Polling rate :", dev.polling_rate, "ms")
	print ("   Wireless PID :", dev.wpid)
	print ("   Serial number:", dev.serial)
	for fw in dev.firmware:
		print ("     %-11s:" % fw.kind, (fw.name + ' ' + fw.version).strip())

	if dev.power_switch_location:
		print ("   The power switch is located on the", dev.power_switch_location)

	from logitech.unifying_receiver import hidpp10, hidpp20
	if p > 0:
		if dev.features:
			print ("   Supports %d HID++ 2.0 features:" % len(dev.features))
			for index, feature in enumerate(dev.features):
				feature = dev.features[index]
				flags = dev.request(0x0000, feature.bytes(2))
				flags = 0 if flags is None else ord(flags[1:2])
				flags = hidpp20.FEATURE_FLAG.flag_names(flags)
				print ("      %2d: %-20s {%04X}   %s" % (index, feature, feature, ', '.join(flags)))

		if dev.keys:
			print ("   Has %d reprogrammable keys:" % len(dev.keys))
			for k in dev.keys:
				flags = hidpp20.KEY_FLAG.flag_names(k.flags)
				print ("      %2d: %-20s => %-20s   %s" % (k.index, k.key, k.task, ', '.join(flags)))

	if p > 0:
		battery = hidpp20.get_battery(dev)
		if battery is None:
			battery = hidpp10.get_battery(dev)
		if battery:
			charge, status = battery
			print ("   Battery is %d%% charged," % charge, status)
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
		dev = _find_device(receiver, args.device, True)
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

	def _notification_handler(n):
		if n.devnumber == 0xFF:
			r_status.process_notification(n)
			if not r_status.lock_open:
				done[0] = True
		elif n.sub_id == 0x41 and n.address == 0x04:
			if n.devnumber not in known_devices:
				r_status.new_device = receiver[n.devnumber]

	from logitech.unifying_receiver import base
	base.notifications_hook = _notification_handler

	# check if it's necessary to set the notification flags
	notification_flags = receiver.request(0x8100)
	if notification_flags:
		# just to see if any bits are set
		notification_flags = ord(notification_flags[:1]) + ord(notification_flags[1:2]) + ord(notification_flags[2:3])
	if not notification_flags:
		# if there are any notifications set, just assume the one we need is already set
		receiver.enable_notifications()
	receiver.set_lock(False, timeout=20)
	print ("Pairing: turn your new device on (timing out in 20 seconds).")

	while not done[0]:
		n = base.read(receiver.handle, 2000)
		if n:
			n = base.make_notification(*n)
			if n:
				_notification_handler(n)

	if not notification_flags:
		# only clear the flags if they weren't set before, otherwise a
		# concurrently running Solaar app will stop working properly
		receiver.enable_notifications(False)
	base.notifications_hook = None

	if r_status.new_device:
		dev = r_status.new_device
		print ("Paired device %d: %s [%s:%s]" % (dev.number, dev.name, dev.codename, dev.serial))
	else:
		_fail(r_status[status.ERROR])


def unpair_device(receiver, args):
	dev = _find_device(receiver, args.device)

	# query these now, it's last chance to get them
	number, name, codename, serial = dev.number, dev.name, dev.codename, dev.serial
	try:
		del receiver[number]
		print ("Unpaired %d: %s [%s:%s]" % (number, name, codename, serial))
	except Exception as e:
		_fail("failed to unpair device %s: %s" % (dev.name, e))


def config_device(receiver, args):
	dev = _find_device(receiver, args.device)
	# if dev is receiver:
	# 	_fail("no settings for the receiver")

	if not dev.settings:
		_fail("no settings for %s" % dev.name)

	if not args.setting:
		print ("[%s:%s]" % (dev.serial, dev.kind))
		print ("#", dev.name)
		for s in dev.settings:
			print ("")
			print ("# %s" % s.label)
			if s.choices:
				print ("#   possible values: one of [", ', '.join(str(v) for v in s.choices), "], or higher/lower/highest/max/lowest/min")
			else:
				print ("#   possible values: on/true/t/yes/y/1 or off/false/f/no/n/0")
			value = s.read()
			if value is None:
				print ("# %s = ? (failed to read from device)" % s.name)
			else:
				print (s.name, "=", value)
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
			if value.lower() in ['1', 'true', 'yes', 'on', 't', 'y']:
				value = True
			elif value.lower() in ['0', 'false', 'no', 'off', 'f', 'n']:
				value = False
			else:
				_fail("don't know how to interpret '%s' as boolean" % value)

	elif setting.choices:
		value = args.value.lower()

		if value in ['higher', 'lower']:
			old_value = setting.read()
			if old_value is None:
				_fail("could not read current value of '%s'" % setting.name)

			if value == 'lower':
				lower_values = setting.choices[:old_value]
				value = lower_values[-1] if lower_values else setting.choices[:][0]
			elif value == 'higher':
				higher_values = setting.choices[old_value + 1:]
				value = higher_values[0] if higher_values else setting.choices[:][-1]
		elif value in ('highest', 'max'):
			value = setting.choices[:][-1]
		elif value in ('lowest', 'min'):
			value = setting.choices[:][0]
		elif value not in setting.choices:
			_fail("possible values for '%s' are: [%s]" % (setting.name, ', '.join(str(v) for v in setting.choices)))
			value = setting.choices[value]

	else:
		raise NotImplemented

	result = setting.write(value)
	if result is None:
		_fail("failed to set '%s' = '%s' [%s]" % (setting.name, value, repr(value)))
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

	if args.debug > 0:
		log_level = logging.WARNING - 10 * args.debug
		log_format='%(asctime)s %(levelname)8s %(name)s: %(message)s'
		logging.basicConfig(level=max(log_level, logging.DEBUG), format=log_format)
	else:
		logging.root.addHandler(logging.NullHandler())
		logging.root.setLevel(logging.ERROR)

	return args


def main():
	_require('pyudev', 'python-pyudev')
	args = _parse_arguments()
	receiver = _receiver()
	args.cmd(receiver, args)

if __name__ == '__main__':
	main()
