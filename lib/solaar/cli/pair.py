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


from time import time as _timestamp

from logitech_receiver import (
				base as _base,
				hidpp10 as _hidpp10,
				status as _status,
				notifications as _notifications,
			)


def run(receivers, args, find_receiver, _ignore):
	assert receivers

	if args.receiver:
		receiver_name = args.receiver.lower()
		receiver = find_receiver(receiver_name)
		if not receiver:
			raise Exception("no receiver found matching '%s'" % receiver_name)
	else:
		receiver = receivers[0]

	assert receiver
	receiver.status = _status.ReceiverStatus(receiver, lambda *args, **kwargs: None)

	# check if it's necessary to set the notification flags
	old_notification_flags = _hidpp10.get_notification_flags(receiver) or 0
	if not (old_notification_flags & _hidpp10.NOTIFICATION_FLAG.wireless):
		_hidpp10.set_notification_flags(receiver, old_notification_flags | _hidpp10.NOTIFICATION_FLAG.wireless)

	# get all current devices
	known_devices = [dev.number for dev in receiver]

	class _HandleWithNotificationHook(int):
		def notifications_hook(self, n):
			assert n
			if n.devnumber == 0xFF:
				_notifications.process(receiver, n)
			elif n.sub_id == 0x41: # allow for other protocols! (was and n.address == 0x04)
				if n.devnumber not in known_devices:
					receiver.status.new_device = receiver[n.devnumber]
				elif receiver.re_pairs:
					del receiver[n.devnumber] # get rid of information on device re-paired away
					receiver.status.new_device = receiver[n.devnumber]

	timeout = 20  # seconds
	receiver.handle = _HandleWithNotificationHook(receiver.handle)

	receiver.set_lock(False, timeout=timeout)
	print ('Pairing: turn your new device on (timing out in', timeout, 'seconds).')

	# the lock-open notification may come slightly later, wait for it a bit
	pairing_start = _timestamp()
	patience = 5  # seconds

	while receiver.status.lock_open or _timestamp() - pairing_start < patience:
		n = _base.read(receiver.handle)
		if n:
			n = _base.make_notification(*n)
			if n:
				receiver.handle.notifications_hook(n)

	if not (old_notification_flags & _hidpp10.NOTIFICATION_FLAG.wireless):
		# only clear the flags if they weren't set before, otherwise a
		# concurrently running Solaar app might stop working properly
		_hidpp10.set_notification_flags(receiver, old_notification_flags)

	if receiver.status.new_device:
		dev = receiver.status.new_device
		print ('Paired device %d: %s (%s) [%s:%s]' % (dev.number, dev.name, dev.codename, dev.wpid, dev.serial))
	else:
		error = receiver.status.get(_status.KEYS.ERROR)
		if error :
			raise Exception("pairing failed: %s" % error)
		else :
			print ('Paired a device') # this is better than an error

