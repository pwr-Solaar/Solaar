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

from time import time

from logitech_receiver import base
from logitech_receiver import hidpp10
from logitech_receiver import hidpp10_constants
from logitech_receiver import notifications

_hidpp10 = hidpp10.Hidpp10()


def run(receivers, args, find_receiver, _ignore):
    assert receivers

    if args.receiver:
        receiver_name = args.receiver.lower()
        receiver = find_receiver(receivers, receiver_name)
        if not receiver:
            raise Exception(f"no receiver found matching '{receiver_name}'")
    else:
        receiver = receivers[0]

    assert receiver

    # check if it's necessary to set the notification flags
    old_notification_flags = _hidpp10.get_notification_flags(receiver) or 0
    if not (old_notification_flags & hidpp10_constants.NOTIFICATION_FLAG.wireless):
        _hidpp10.set_notification_flags(receiver, old_notification_flags | hidpp10_constants.NOTIFICATION_FLAG.wireless)

    # get all current devices
    known_devices = [dev.number for dev in receiver]

    class _HandleWithNotificationHook(int):
        def notifications_hook(self, n):
            nonlocal known_devices
            assert n
            if n.devnumber == 0xFF:
                notifications.process(receiver, n)
            elif n.sub_id == 0x41 and len(n.data) == base.SHORT_MESSAGE_SIZE - 4:
                kd, known_devices = known_devices, None  # only process one connection notification
                if kd is not None:
                    if n.devnumber not in kd:
                        receiver.pairing.new_device = receiver.register_new_device(n.devnumber, n)
                    elif receiver.re_pairs:
                        del receiver[n.devnumber]  # get rid of information on device re-paired away
                        receiver.pairing.new_device = receiver.register_new_device(n.devnumber, n)

    timeout = 30  # seconds
    receiver.handle = _HandleWithNotificationHook(receiver.handle)

    if receiver.receiver_kind == "bolt":  # Bolt receivers require authentication to pair a device
        receiver.discover(timeout=timeout)
        print("Bolt Pairing: long-press the pairing key or button on your device (timing out in", timeout, "seconds).")
        pairing_start = time()
        patience = 5  # the discovering notification may come slightly later, so be patient
        while receiver.pairing.discovering or time() - pairing_start < patience:
            if receiver.pairing.device_address and receiver.pairing.device_authentication and receiver.pairing.device_name:
                break
            n = base.read(receiver.handle)
            n = base.make_notification(*n) if n else None
            if n:
                receiver.handle.notifications_hook(n)
        address = receiver.pairing.device_address
        name = receiver.pairing.device_name
        authentication = receiver.pairing.device_authentication
        kind = receiver.pairing.device_kind
        print(f"Bolt Pairing: discovered {name}")
        receiver.pair_device(
            address=address,
            authentication=authentication,
            entropy=20 if kind == hidpp10_constants.DEVICE_KIND.keyboard else 10,
        )
        pairing_start = time()
        patience = 5  # the discovering notification may come slightly later, so be patient
        while receiver.pairing.lock_open or time() - pairing_start < patience:
            if receiver.pairing.device_passkey:
                break
            n = base.read(receiver.handle)
            n = base.make_notification(*n) if n else None
            if n:
                receiver.handle.notifications_hook(n)
        if authentication & 0x01:
            print(f"Bolt Pairing: type passkey {receiver.pairing.device_passkey} and then press the enter key")
        else:
            passkey = f"{int(receiver.pairing.device_passkey):010b}"
            passkey = ", ".join(["right" if bit == "1" else "left" for bit in passkey])
            print(f"Bolt Pairing: press {passkey}")
            print("and then press left and right buttons simultaneously")
        while receiver.pairing.lock_open:
            n = base.read(receiver.handle)
            n = base.make_notification(*n) if n else None
            if n:
                receiver.handle.notifications_hook(n)

    else:
        receiver.set_lock(False, timeout=timeout)
        print("Pairing: Turn your device on or press, hold, and release")
        print("a channel button or the channel switch button.")
        print("Timing out in", timeout, "seconds.")
        pairing_start = time()
        patience = 5  # the lock-open notification may come slightly later, wait for it a bit
        while receiver.pairing.lock_open or time() - pairing_start < patience:
            n = base.read(receiver.handle)
            if n:
                n = base.make_notification(*n)
                if n:
                    receiver.handle.notifications_hook(n)

    if not (old_notification_flags & hidpp10_constants.NOTIFICATION_FLAG.wireless):
        # only clear the flags if they weren't set before, otherwise a
        # concurrently running Solaar app might stop working properly
        _hidpp10.set_notification_flags(receiver, old_notification_flags)

    if receiver.pairing.new_device:
        dev = receiver.pairing.new_device
        print(f"Paired device {int(dev.number)}: {dev.name} ({dev.codename}) [{dev.wpid}:{dev.serial}]")
    else:
        error = receiver.pairing.error
        if error:
            raise Exception(f"pairing failed: {error}")
        else:
            print("Paired device")  # this is better than an error
