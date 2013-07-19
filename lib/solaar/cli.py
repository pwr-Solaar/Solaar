#!/usr/bin/env python
# -*- python-mode -*-
# -*- coding: UTF-8 -*-

## Copyright (C) 2012-2013  Daniel Pavel
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with this program; if not, write to the Free Software Foundation, Inc.,
## 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

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

def _receiver(dev_path=None):
	from logitech_receiver import Receiver
	from logitech_receiver.base import receivers
	for dev_info in receivers():
		if dev_path is not None and dev_path != dev_info.path:
			continue
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
			if number < 1 or number > receiver.max_devices:
				_fail("%s (%s) supports device numbers 1 to %d" % (receiver.name, receiver.path, receiver.max_devices))
			dev = receiver[number]
			if dev is None:
				_fail("no paired device with number %s" % number)
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
		print ("Unifying Receiver [%s:%s] with %d devices" % (receiver.path, receiver.serial, paired_count))
		return

	print ("Unifying Receiver")
	print ("   Device path  :", receiver.path)
	print ("   USB id       : 046d:%s" % receiver.product_id)
	print ("   Serial       :", receiver.serial)
	for f in receiver.firmware:
		print ("     %-11s: %s" % (f.kind, f.version))

	print ("   Has", paired_count, "paired device(s) out of a maximum of", receiver.max_devices, ".")

	from logitech_receiver import hidpp10
	notification_flags = hidpp10.get_notification_flags(receiver)
	if notification_flags is not None:
		if notification_flags:
			notification_names = hidpp10.NOTIFICATION_FLAG.flag_names(notification_flags)
			print ("   Notifications: 0x%06X = %s" % (notification_flags, ', '.join(notification_names)))
		else:
			print ("   Notifications: (none)")

	activity = receiver.read_register(hidpp10.REGISTERS.devices_activity)
	if activity:
		activity = [(d, ord(activity[d - 1:d])) for d in range(1, receiver.max_devices)]
		activity_text = ', '.join(('%d=%d' % (d, a)) for d, a in activity if a > 0)
		print ("   Device activity counters:", activity_text or '(empty)')


def _print_device(dev, verbose=False):
	assert dev
	state = '' if dev.ping() else 'offline'

	if not verbose:
		print ("%d: %s [%s:%s]" % (dev.number, dev.name, dev.codename, dev.serial), state)
		return

	print ("%d: %s" % (dev.number, dev.name))
	print ("   Codename     :", dev.codename)
	print ("   Kind         :", dev.kind)
	print ("   Wireless PID :", dev.wpid)
	if dev.protocol:
		print ("   Protocol     : HID++ %1.1f" % dev.protocol)
	else:
		print ("   Protocol     : unknown (device is offline)")
	print ("   Polling rate :", dev.polling_rate, "ms")
	print ("   Serial number:", dev.serial)
	for fw in dev.firmware:
		print ("     %11s:" % fw.kind, (fw.name + ' ' + fw.version).strip())

	if dev.power_switch_location:
		print ("   The power switch is located on the %s." % dev.power_switch_location)

	from logitech_receiver import hidpp10, hidpp20, special_keys

	if dev.online:
		notification_flags = hidpp10.get_notification_flags(dev)
		if notification_flags is not None:
			if notification_flags:
				notification_names = hidpp10.NOTIFICATION_FLAG.flag_names(notification_flags)
				print ("   Notifications: 0x%06X = %s." % (notification_flags, ', '.join(notification_names)))
			else:
				print ("   Notifications: (none).")

	if dev.online:
		if dev.features:
			print ("   Supports %d HID++ 2.0 features:" % len(dev.features))
			for index, feature in enumerate(dev.features):
				feature = dev.features[index]
				flags = dev.request(0x0000, feature.bytes(2))
				flags = 0 if flags is None else ord(flags[1:2])
				flags = hidpp20.FEATURE_FLAG.flag_names(flags)
				print ("      %2d: %-22s {%04X}   %s" % (index, feature, feature, ', '.join(flags)))

	if dev.online:
		if dev.keys:
			print ("   Has %d reprogrammable keys:" % len(dev.keys))
			for k in dev.keys:
				flags = special_keys.KEY_FLAG.flag_names(k.flags)
				print ("      %2d: %-26s => %-27s   %s" % (k.index, k.key, k.task, ', '.join(flags)))

	if dev.online:
		battery = hidpp20.get_battery(dev)
		if battery is None:
			battery = hidpp10.get_battery(dev)
		if battery is not None:
			from logitech_receiver.common import NamedInt as _NamedInt
			level, status = battery
			if isinstance(level, _NamedInt):
				text = str(level)
			else:
				text = '%d%%' % level
			print ("   Battery: %s, %s," % (text, status))
		else:
			print ("   Battery status unavailable.")
	else:
		print ("   Battery status is unknown (device is offline).")

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

	from logitech_receiver import base, hidpp10, status, notifications
	receiver.status = status.ReceiverStatus(receiver, lambda *args, **kwargs: None)

	# check if it's necessary to set the notification flags
	old_notification_flags = hidpp10.get_notification_flags(receiver) or 0
	if not (old_notification_flags & hidpp10.NOTIFICATION_FLAG.wireless):
		hidpp10.set_notification_flags(receiver, old_notification_flags | hidpp10.NOTIFICATION_FLAG.wireless)

	class HandleWithNotificationHook(int):
		def notifications_hook(self, n):
			assert n
			if n.devnumber == 0xFF:
				notifications.process(receiver, n)
			elif n.sub_id == 0x41 and n.address == 0x04:
				if n.devnumber not in known_devices:
					receiver.status.new_device = receiver[n.devnumber]

	timeout = 20  # seconds
	receiver.handle = HandleWithNotificationHook(receiver.handle)
	receiver.set_lock(False, timeout=timeout)
	print ("Pairing: turn your new device on (timing out in", timeout, "seconds).")

	# the lock-open notification may come slightly later, wait for it a bit
	from time import time as timestamp
	pairing_start = timestamp()
	patience = 5  # seconds

	while receiver.status.lock_open or timestamp() - pairing_start < patience:
		n = base.read(receiver.handle)
		if n:
			n = base.make_notification(*n)
			if n:
				receiver.handle.notifications_hook(n)

	if not (old_notification_flags & hidpp10.NOTIFICATION_FLAG.wireless):
		# only clear the flags if they weren't set before, otherwise a
		# concurrently running Solaar app might stop working properly
		hidpp10.set_notification_flags(receiver, old_notification_flags)

	if receiver.status.new_device:
		dev = receiver.status.new_device
		print ("Paired device %d: %s [%s:%s:%s]" % (dev.number, dev.name, dev.wpid, dev.codename, dev.serial))
	else:
		error = receiver.status[status.KEYS.ERROR] or 'no device detected?'
		_fail(error)


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

	from logitech_receiver import settings as _settings

	if setting.kind == _settings.KIND.toggle:
		value = args.value
		try:
			value = bool(int(value))
		except:
			if value.lower() in ('1', 'true', 'yes', 'on', 't', 'y'):
				value = True
			elif value.lower() in ('0', 'false', 'no', 'off', 'f', 'n'):
				value = False
			else:
				_fail("don't know how to interpret '%s' as boolean" % value)

	elif setting.choices:
		value = args.value.lower()

		if value in ('higher', 'lower'):
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
		_fail("failed to set '%s' = '%s' [%r]" % (setting.name, value, value))
	print ("%s = %s" % (setting.name, result))

#
#
#

def _parse_arguments():
	from argparse import ArgumentParser
	arg_parser = ArgumentParser(prog=NAME.lower())
	arg_parser.add_argument('-d', '--debug', action='count', default=0,
							help='print logging messages, for debugging purposes (may be repeated for extra verbosity)')
	arg_parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__)
	arg_parser.add_argument('-D', '--hidraw', action='store', dest='hidraw_path', metavar='PATH',
					help='unifying receiver to use; the first detected receiver if unspecified. Example: /dev/hidraw2')

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

	# Python 3 has an undocumented 'feature' that breaks parsing empty args
	# http://bugs.python.org/issue16308
	if not 'cmd' in args:
		arg_parser.print_usage(sys.stderr)
		sys.stderr.write('%s: error: too few arguments\n' % NAME.lower())
		sys.exit(2)

	if args.debug > 0:
		log_level = logging.WARNING - 10 * args.debug
		log_format='%(asctime)s,%(msecs)03d %(levelname)8s %(name)s: %(message)s'
		logging.basicConfig(level=max(log_level, logging.DEBUG), format=log_format, datefmt='%H:%M:%S')
	else:
		logging.root.addHandler(logging.NullHandler())
		logging.root.setLevel(logging.ERROR)

	return args


def main():
	_require('pyudev', 'python-pyudev')
	args = _parse_arguments()
	receiver = _receiver(args.hidraw_path)
	args.cmd(receiver, args)

if __name__ == '__main__':
	main()
