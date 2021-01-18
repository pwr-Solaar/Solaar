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

import errno as _errno

from logging import INFO as _INFO
from logging import getLogger

from . import base as _base
from . import hidpp10 as _hidpp10
from .base_usb import product_information as _product_information
from .common import strhex as _strhex
from .device import Device

_log = getLogger(__name__)
del getLogger

_R = _hidpp10.REGISTERS

#
#
#


class Receiver(object):
    """A Unifying Receiver instance.

    The paired devices are available through the sequence interface.
    """
    number = 0xFF
    kind = None

    def __init__(self, handle, device_info):
        assert handle
        self.handle = handle
        assert device_info
        self.path = device_info.path
        self.isDevice = False  # some devices act as receiver so we need a property to distinguish them
        # USB product id, used for some Nano receivers
        self.product_id = device_info.product_id
        product_info = _product_information(self.product_id)
        if not product_info:
            raise Exception('Unknown receiver type', self.product_id)

        # read the serial immediately, so we can find out max_devices
        serial_reply = self.read_register(_R.receiver_info, 0x03)
        if serial_reply:
            self.serial = _strhex(serial_reply[1:5])
            self.max_devices = ord(serial_reply[6:7])
            if self.max_devices <= 0 or self.max_devices > 6:
                self.max_devices = product_info.get('max_devices', 1)
            # TODO _properly_ figure out which receivers do and which don't support unpairing
            # This code supposes that receivers that don't unpair support a pairing request for device index 0
            self.may_unpair = self.write_register(_R.receiver_pairing) is None
        else:  # handle receivers that don't have a serial number specially (i.e., c534)
            self.serial = None
            self.max_devices = product_info.get('max_devices', 1)
            self.may_unpair = product_info.get('may_unpair', False)

        self.name = product_info.get('name', '')
        self.re_pairs = product_info.get('re_pairs', False)
        self._str = '<%s(%s,%s%s)>' % (
            self.name.replace(' ', ''), self.path, '' if isinstance(self.handle, int) else 'T', self.handle
        )
        self.ex100_27mhz_wpid_fix = product_info.get('ex100_27mhz_wpid_fix', False)

        self._firmware = None
        self._devices = {}
        self._remaining_pairings = None

    def close(self):
        handle, self.handle = self.handle, None
        self._devices.clear()
        return (handle and _base.close(handle))

    def __del__(self):
        self.close()

    @property
    def firmware(self):
        if self._firmware is None and self.handle:
            self._firmware = _hidpp10.get_firmware(self)
        return self._firmware

    # how many pairings remain (None for unknown, -1 for unlimited)
    def remaining_pairings(self, cache=True):
        if self._remaining_pairings is None or not cache:
            ps = self.read_register(_R.receiver_connection)
            if ps is not None:
                ps = ord(ps[2:3])
                self._remaining_pairings = ps - 5 if ps >= 5 else -1
        return self._remaining_pairings

    def enable_connection_notifications(self, enable=True):
        """Enable or disable device (dis)connection notifications on this
        receiver."""
        if not self.handle:
            return False

        if enable:
            set_flag_bits = (
                _hidpp10.NOTIFICATION_FLAG.battery_status
                | _hidpp10.NOTIFICATION_FLAG.wireless
                | _hidpp10.NOTIFICATION_FLAG.software_present
            )
        else:
            set_flag_bits = 0
        ok = _hidpp10.set_notification_flags(self, set_flag_bits)
        if ok is None:
            _log.warn('%s: failed to %s receiver notifications', self, 'enable' if enable else 'disable')
            return None

        flag_bits = _hidpp10.get_notification_flags(self)
        flag_names = None if flag_bits is None else tuple(_hidpp10.NOTIFICATION_FLAG.flag_names(flag_bits))
        if _log.isEnabledFor(_INFO):
            _log.info('%s: receiver notifications %s => %s', self, 'enabled' if enable else 'disabled', flag_names)
        return flag_bits

    def notify_devices(self):
        """Scan all devices."""
        if self.handle:
            if not self.write_register(_R.receiver_connection, 0x02):
                _log.warn('%s: failed to trigger device link notifications', self)

    def register_new_device(self, number, notification=None):
        if self._devices.get(number) is not None:
            raise IndexError('%s: device number %d already registered' % (self, number))

        assert notification is None or notification.devnumber == number
        assert notification is None or notification.sub_id == 0x41

        try:
            dev = Device(self, number, notification)
            assert dev.wpid
            if _log.isEnabledFor(_INFO):
                _log.info('%s: found new device %d (%s)', self, number, dev.wpid)
            self._devices[number] = dev
            return dev
        except _base.NoSuchDevice:
            _log.exception('register_new_device')

        _log.warning('%s: looked for device %d, not found', self, number)
        self._devices[number] = None

    def set_lock(self, lock_closed=True, device=0, timeout=0):
        if self.handle:
            action = 0x02 if lock_closed else 0x01
            reply = self.write_register(_R.receiver_pairing, action, device, timeout)
            if reply:
                return True
            _log.warn('%s: failed to %s the receiver lock', self, 'close' if lock_closed else 'open')

    def count(self):
        count = self.read_register(_R.receiver_connection)
        return 0 if count is None else ord(count[1:2])

    # def has_devices(self):
    #     return len(self) > 0 or self.count() > 0

    def request(self, request_id, *params):
        if bool(self):
            return _base.request(self.handle, 0xFF, request_id, *params)

    read_register = _hidpp10.read_register
    write_register = _hidpp10.write_register

    def __iter__(self):
        for number in range(1, 1 + self.max_devices):
            if number in self._devices:
                dev = self._devices[number]
            else:
                dev = self.__getitem__(number)
            if dev is not None:
                yield dev

    def __getitem__(self, key):
        if not bool(self):
            return None

        dev = self._devices.get(key)
        if dev is not None:
            return dev

        if not isinstance(key, int):
            raise TypeError('key must be an integer')
        if key < 1 or key > self.max_devices:
            raise IndexError(key)

        return self.register_new_device(key)

    def __delitem__(self, key):
        self._unpair_device(key, False)

    def _unpair_device(self, key, force=False):
        key = int(key)

        if self._devices.get(key) is None:
            raise IndexError(key)

        dev = self._devices[key]
        if not dev:
            if key in self._devices:
                del self._devices[key]
            return

        if self.re_pairs and not force:
            # invalidate the device, but these receivers don't unpair per se
            dev.online = False
            dev.wpid = None
            if key in self._devices:
                del self._devices[key]
            _log.warn('%s removed device %s', self, dev)
        else:
            reply = self.write_register(_R.receiver_pairing, 0x03, key)
            if reply:
                # invalidate the device
                dev.online = False
                dev.wpid = None
                if key in self._devices:
                    del self._devices[key]
                if _log.isEnabledFor(_INFO):
                    _log.info('%s unpaired device %s', self, dev)
            else:
                _log.error('%s failed to unpair device %s', self, dev)
                raise Exception('failed to unpair device %s: %s' % (dev.name, key))

    def __len__(self):
        return len([d for d in self._devices.values() if d is not None])

    def __contains__(self, dev):
        if isinstance(dev, int):
            return self._devices.get(dev) is not None

        return self.__contains__(dev.number)

    def __eq__(self, other):
        return other is not None and self.kind == other.kind and self.path == other.path

    def __ne__(self, other):
        return other is None or self.kind != other.kind or self.path != other.path

    def __hash__(self):
        return self.path.__hash__()

    def __str__(self):
        return self._str

    __unicode__ = __repr__ = __str__

    __bool__ = __nonzero__ = lambda self: self.handle is not None

    @classmethod
    def open(self, device_info):
        """Opens a Logitech Receiver found attached to the machine, by Linux device path.

        :returns: An open file handle for the found receiver, or ``None``.
        """
        try:
            handle = _base.open_path(device_info.path)
            if handle:
                return Receiver(handle, device_info)
        except OSError as e:
            _log.exception('open %s', device_info)
            if e.errno == _errno.EACCES:
                raise
        except Exception:
            _log.exception('open %s', device_info)
