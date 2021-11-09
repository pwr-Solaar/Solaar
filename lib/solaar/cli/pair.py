# -*- python-mode -*-

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

from time import time as _timestamp

from logitech_receiver import base as _base
from logitech_receiver import hidpp10 as _hidpp10
from logitech_receiver import notifications as _notifications
from logitech_receiver import status as _status

_R = _hidpp10.REGISTERS


def run(receivers, args, find_receiver, _ignore):
    assert receivers

    if args.receiver:
        receiver_name = args.receiver.lower()
        receiver = find_receiver(receivers, receiver_name)
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
            nonlocal known_devices
            assert n
            if n.devnumber == 0xFF:
                _notifications.process(receiver, n)
            elif n.sub_id == 0x41 and len(n.data) == _base._SHORT_MESSAGE_SIZE - 4:
                kd, known_devices = known_devices, None  # only process one connection notification
                if kd is not None:
                    if n.devnumber not in kd:
                        receiver.status.new_device = receiver.register_new_device(n.devnumber, n)
                    elif receiver.re_pairs:
                        del receiver[n.devnumber]  # get rid of information on device re-paired away
                        receiver.status.new_device = receiver.register_new_device(n.devnumber, n)

    timeout = 30  # seconds
    receiver.handle = _HandleWithNotificationHook(receiver.handle)

    if receiver.receiver_kind == 'bolt':  # Bolt receivers require authentication to pair a device
        receiver.discover(timeout=timeout)
        print('Bolt Pairing: long-press the pairing key or button on your device (timing out in', timeout, 'seconds).')
        pairing_start = _timestamp()
        patience = 5  # the discovering notification may come slightly later, so be patient
        while receiver.status.discovering or _timestamp() - pairing_start < patience:
            if receiver.status.device_address and receiver.status.device_authentication and receiver.status.device_name:
                break
            n = _base.read(receiver.handle)
            n = _base.make_notification(*n) if n else None
            if n:
                receiver.handle.notifications_hook(n)
        address = receiver.status.device_address
        name = receiver.status.device_name
        authentication = receiver.status.device_authentication
        kind = receiver.status.device_kind
        print(f'Bolt Pairing: discovered {name}')
        receiver.pair_device(
            address=address, authentication=authentication, entropy=20 if kind == _hidpp10.DEVICE_KIND.keyboard else 10
        )
        pairing_start = _timestamp()
        patience = 5  # the discovering notification may come slightly later, so be patient
        while receiver.status.lock_open or _timestamp() - pairing_start < patience:
            if receiver.status.device_passkey:
                break
            n = _base.read(receiver.handle)
            n = _base.make_notification(*n) if n else None
            if n:
                receiver.handle.notifications_hook(n)
        if authentication & 0x01:
            print(f'Bolt Pairing: type passkey {receiver.status.device_passkey} and then press the enter key')
        else:
            passkey = f'{int(receiver.status.device_passkey):010b}'
            passkey = ', '.join(['right' if bit == '1' else 'left' for bit in passkey])
            print(f'Bolt Pairing: press {passkey}')
            print('and then press left and right buttons simultaneously')
        while receiver.status.lock_open:
            n = _base.read(receiver.handle)
            n = _base.make_notification(*n) if n else None
            if n:
                receiver.handle.notifications_hook(n)

    else:
        receiver.set_lock(False, timeout=timeout)
        print('Pairing: turn your new device on (timing out in', timeout, 'seconds).')
        pairing_start = _timestamp()
        patience = 5  # the lock-open notification may come slightly later, wait for it a bit
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
        print('Paired device %d: %s (%s) [%s:%s]' % (dev.number, dev.name, dev.codename, dev.wpid, dev.serial))
    else:
        error = receiver.status.get(_status.KEYS.ERROR)
        if error:
            raise Exception('pairing failed: %s' % error)
        else:
            print('Paired device')  # this is better than an error
