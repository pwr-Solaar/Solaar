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


from solaar import configuration as _configuration
from logitech_receiver import settings as _settings


def _print_setting(s, verbose=True):
	print ('#', s.label)
	if verbose:
		if s.description:
			print ('#', s.description.replace('\n', ' '))
		if s.kind == _settings.KIND.toggle:
			print ('#   possible values: on/true/t/yes/y/1 or off/false/f/no/n/0')
		elif s.choices:
			print ('#   possible values: one of [', ', '.join(str(v) for v in s.choices), '], or higher/lower/highest/max/lowest/min')
		else:
			# wtf?
			pass
	value = s.read(cached=False)
	if value is None:
		print (s.name, '= ? (failed to read from device)')
	else:
		print (s.name, '= %r' % value)


def run(receivers, args, find_receiver, find_device):
	assert receivers
	assert args.device

	device_name = args.device.lower()
	dev = find_device(receivers, device_name)

	if not dev.ping():
		raise Exception('%s is offline' % dev.name)

	if not dev.settings:
		raise Exception('no settings for %s' % dev.name)

	_configuration.attach_to(dev)

	if not args.setting:
		print (dev.name, '(%s) [%s:%s]' % (dev.codename, dev.wpid, dev.serial))
		for s in dev.settings:
			print ('')
			_print_setting(s)
		return

	setting_name = args.setting.lower()
	setting = None
	for s in dev.settings:
		if setting_name == s.name.lower():
			setting = s
			break
	if setting is None:
		raise Exception("no setting '%s' for %s" % (args.setting, dev.name))

	if args.value is None:
		_print_setting(setting)
		return

	if setting.kind == _settings.KIND.toggle:
		value = args.value
		try:
			value = bool(int(value))
		except:
			if value.lower() in ('true', 'yes', 'on', 't', 'y'):
				value = True
			elif value.lower() in ('false', 'no', 'off', 'f', 'n'):
				value = False
			else:
				raise Exception("don't know how to interpret '%s' as boolean" % value)

	elif setting.choices:
		value = args.value.lower()

		if value in ('higher', 'lower'):
			old_value = setting.read()
			if old_value is None:
				raise Exception("could not read current value of '%s'" % setting.name)

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
			raise Exception("possible values for '%s' are: [%s]" % (setting.name, ', '.join(str(v) for v in setting.choices)))
			value = setting.choices[value]

	elif setting.kind == _settings.KIND.range:
		try:
			value = int(args.value)
		except ValueError:
			raise Exception("can't interpret '%s' as integer" % args.value)

	else:
		raise NotImplemented

	result = setting.write(value)
	if result is None:
		raise Exception("failed to set '%s' = '%s' [%r]" % (setting.name, str(value), value))
	_print_setting(setting, False)
