## Copyright (C) 2012-2013  Daniel Pavel
## Copyright (C) 2014-2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
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

import errno as _errno
import logging

import hidapi as _hid

from . import base as _base
from . import exceptions, hidpp10, hidpp10_constants
from .device import Device

logger = logging.getLogger(__name__)

_hidpp10 = hidpp10.Hidpp10()
_R = hidpp10_constants.REGISTERS
_IR = hidpp10_constants.INFO_SUBREGISTERS


class ReceiverFactory:
    @staticmethod
    def create_receiver(device_info, setting_callback=None):
        """Opens a Logitech Receiver found attached to the machine, by Linux device path.

        :returns: An open file handle for the found receiver, or ``None``.
        """
        try:
            product_info = _base.product_information(device_info.product_id)
            if not product_info:
                logger.warning("Unknown receiver type: %s", device_info.product_id)
                product_info = {}

            handle = _base.open_path(device_info.path)
            if handle:
                return Receiver(product_info, handle, device_info.path, device_info.product_id, setting_callback)
        except OSError as e:
            logger.exception("open %s", device_info)
            if e.errno == _errno.EACCES:
                raise
        except Exception:
            logger.exception("open %s", device_info)


class Receiver:
    """A Unifying Receiver instance.

    The paired devices are available through the sequence interface.
    """

    number = 0xFF
    kind = None

    def __init__(self, product_info, handle, path, product_id, setting_callback=None):
        assert handle
        self.isDevice = False  # some devices act as receiver so we need a property to distinguish them
        self.handle = handle
        self.path = path
        self.product_id = product_id
        self.setting_callback = setting_callback
        self.receiver_kind = product_info.get("receiver_kind", "unknown")

        # read the serial immediately, so we can find out max_devices
        if self.receiver_kind == "bolt":
            serial_reply = self.read_register(_R.bolt_uniqueId)
            self.serial = serial_reply.hex().upper()
            self.max_devices = product_info.get("max_devices", 1)
            self.may_unpair = product_info.get("may_unpair", False)
        else:
            serial_reply = self.read_register(_R.receiver_info, _IR.receiver_information)
            if serial_reply:
                self.serial = serial_reply[1:5].hex().upper()
                self.max_devices = ord(serial_reply[6:7])
                if self.max_devices <= 0 or self.max_devices > 6:
                    self.max_devices = product_info.get("max_devices", 1)
                self.may_unpair = product_info.get("may_unpair", False)
            else:  # handle receivers that don't have a serial number specially (i.e., c534 and Bolt receivers)
                self.serial = None
                self.max_devices = product_info.get("max_devices", 1)
                self.may_unpair = product_info.get("may_unpair", False)

        self.name = product_info.get("name", "Receiver")
        self.re_pairs = product_info.get("re_pairs", False)
        self._str = "<%s(%s,%s%s)>" % (
            self.name.replace(" ", ""),
            self.path,
            "" if isinstance(self.handle, int) else "T",
            self.handle,
        )

        self._firmware = None
        self._devices = {}
        self._remaining_pairings = None

    def close(self):
        handle, self.handle = self.handle, None
        for _n, d in self._devices.items():
            if d:
                d.close()
        self._devices.clear()
        return handle and _base.close(handle)

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
                hidpp10_constants.NOTIFICATION_FLAG.battery_status
                | hidpp10_constants.NOTIFICATION_FLAG.wireless
                | hidpp10_constants.NOTIFICATION_FLAG.software_present
            )
        else:
            set_flag_bits = 0
        ok = _hidpp10.set_notification_flags(self, set_flag_bits)
        if ok is None:
            logger.warning("%s: failed to %s receiver notifications", self, "enable" if enable else "disable")
            return None

        flag_bits = _hidpp10.get_notification_flags(self)
        flag_names = None if flag_bits is None else tuple(hidpp10_constants.NOTIFICATION_FLAG.flag_names(flag_bits))
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: receiver notifications %s => %s", self, "enabled" if enable else "disabled", flag_names)
        return flag_bits

    def device_codename(self, n):
        if self.receiver_kind == "bolt":
            codename = self.read_register(_R.receiver_info, _IR.bolt_device_name + n, 0x01)
            if codename:
                codename = codename[3 : 3 + min(14, ord(codename[2:3]))]
                return codename.decode("ascii")
        else:
            codename = self.read_register(_R.receiver_info, _IR.device_name + n - 1)
            if codename:
                codename = codename[2 : 2 + ord(codename[1:2])]
                return codename.decode("ascii")

    def device_pairing_information(self, n: int) -> dict:
        """Return information from pairing registers (and elsewhere when necessary)"""
        if self.receiver_kind == "bolt":
            pair_info = self.read_register(_R.receiver_info, _IR.bolt_pairing_information + n)
            if pair_info:
                wpid = (pair_info[3:4] + pair_info[2:3]).hex().upper()
                kind = hidpp10_constants.DEVICE_KIND[pair_info[1] & 0x0F]
                serial = pair_info[4:8].hex().upper()
                return {"wpid": wpid, "kind": kind, "polling": None, "serial": serial, "power_switch": "(unknown)"}
            else:
                raise exceptions.NoSuchDevice(number=n, receiver=self, error="can't read Bolt pairing register")
        polling_rate = ""
        serial = None
        power_switch = "(unknown)"
        pair_info = self.read_register(_R.receiver_info, _IR.pairing_information + n - 1)
        if pair_info:  # either a Unifying receiver or a Unifying-ready receiver
            wpid = pair_info[3:5].hex().upper()
            kind = hidpp10_constants.DEVICE_KIND[pair_info[7] & 0x0F]
            polling_rate = str(ord(pair_info[2:3])) + "ms"
        elif self.receiver_kind == "27Mz":  # 27Mhz receiver, extract WPID from udev path
            wpid = _hid.find_paired_node_wpid(self.path, n)
            if not wpid:
                logger.error("Unable to get wpid from udev for device %d of %s", n, self)
                raise exceptions.NoSuchDevice(number=n, receiver=self, error="Not present 27Mhz device")
            kind = hidpp10_constants.DEVICE_KIND[self.get_kind_from_index(n)]
        elif not self.receiver_kind == "unifying":  # may be an old Nano receiver
            device_info = self.read_register(_R.receiver_info, 0x04)
            if device_info:
                wpid = device_info[3:5].hex().upper()
                kind = hidpp10_constants.DEVICE_KIND[0x00]  # unknown kind
            else:
                raise exceptions.NoSuchDevice(number=n, receiver=self, error="read pairing information - non-unifying")
        else:
            raise exceptions.NoSuchDevice(number=n, receiver=self, error="read pairing information")
        pair_info = self.read_register(_R.receiver_info, _IR.extended_pairing_information + n - 1)
        if pair_info:
            power_switch = hidpp10_constants.POWER_SWITCH_LOCATION[pair_info[9] & 0x0F]
        else:  # some Nano receivers?
            pair_info = self.read_register(0x2D5)
        if pair_info:
            serial = pair_info[1:5].hex().upper()
        return {"wpid": wpid, "kind": kind, "polling": polling_rate, "serial": serial, "power_switch": power_switch}

    def get_kind_from_index(self, index):
        """Get device kind from 27Mhz device index"""
        # From drivers/hid/hid-logitech-dj.c
        if index == 1:  # mouse
            kind = 2
        elif index == 2:  # mouse
            kind = 2
        elif index == 3:  # keyboard
            kind = 1
        elif index == 4:  # numpad
            kind = 3
        else:  # unknown device number on 27Mhz receiver
            logger.error("failed to calculate device kind for device %d of %s", index, self)
            raise exceptions.NoSuchDevice(number=index, receiver=self, error="Unknown 27Mhz device number")
        return kind

    def notify_devices(self):
        """Scan all devices."""
        if self.handle:
            if not self.write_register(_R.receiver_connection, 0x02):
                logger.warning("%s: failed to trigger device link notifications", self)

    def register_new_device(self, number, notification=None):
        if self._devices.get(number) is not None:
            raise IndexError("%s: device number %d already registered" % (self, number))

        assert notification is None or notification.devnumber == number
        assert notification is None or notification.sub_id == 0x41

        try:
            info = self.device_pairing_information(number)
            if notification is not None:
                online = not bool(ord(notification.data[0:1]) & 0x40)
                # the rest may be redundant, but keep it around for now
                info["wpid"] = (notification.data[2:3] + notification.data[1:2]).hex().upper()
                kind = ord(notification.data[0:1]) & 0x0F
                if self.receiver_kind == "27Mhz":  # get 27Mhz wpid and set kind based on index
                    info["wpid"] = "00" + notification.data[2:3].hex().upper()
                    kind = self.get_kind_from_index(number)
                info["kind"] = hidpp10_constants.DEVICE_KIND[kind]
            else:
                online = True
            dev = Device(self, number, online, pairing_info=info, setting_callback=self.setting_callback)
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: found new device %d (%s)", self, number, dev.wpid)
            self._devices[number] = dev
            return dev
        except exceptions.NoSuchDevice as e:
            logger.warning("register new device failed for %s device %d error %s", e.receiver, e.number, e.error)

        logger.warning("%s: looked for device %d, not found", self, number)
        self._devices[number] = None

    def set_lock(self, lock_closed=True, device=0, timeout=0):
        if self.handle:
            action = 0x02 if lock_closed else 0x01
            reply = self.write_register(_R.receiver_pairing, action, device, timeout)
            if reply:
                return True
            logger.warning("%s: failed to %s the receiver lock", self, "close" if lock_closed else "open")

    def discover(self, cancel=False, timeout=30):  # Bolt device discovery
        assert self.receiver_kind == "bolt"
        if self.handle:
            action = 0x02 if cancel else 0x01
            reply = self.write_register(_R.bolt_device_discovery, timeout, action)
            if reply:
                return True
            logger.warning("%s: failed to %s device discovery", self, "cancel" if cancel else "start")

    def pair_device(self, pair=True, slot=0, address=b"\0\0\0\0\0\0", authentication=0x00, entropy=20):  # Bolt pairing
        assert self.receiver_kind == "bolt"
        if self.handle:
            action = 0x01 if pair is True else 0x03 if pair is False else 0x02
            reply = self.write_register(_R.bolt_pairing, action, slot, address, authentication, entropy)
            if reply:
                return True
            logger.warning("%s: failed to %s device %s", self, "pair" if pair else "unpair", address)

    def count(self):
        count = self.read_register(_R.receiver_connection)
        return 0 if count is None else ord(count[1:2])

    # def has_devices(self):
    #     return len(self) > 0 or self.count() > 0

    def request(self, request_id, *params):
        if bool(self):
            return _base.request(self.handle, 0xFF, request_id, *params)

    read_register = hidpp10.read_register
    write_register = hidpp10.write_register

    def __iter__(self):
        connected_devices = self.count()
        found_devices = 0
        for number in range(1, 8):  # some receivers have devices past their max # devices
            if found_devices >= connected_devices:
                return
            if number in self._devices:
                dev = self._devices[number]
            else:
                dev = self.__getitem__(number)
            if dev is not None:
                found_devices += 1
                yield dev

    def __getitem__(self, key):
        if not bool(self):
            return None

        dev = self._devices.get(key)
        if dev is not None:
            return dev

        if not isinstance(key, int):
            raise TypeError("key must be an integer")
        if key < 1 or key > 15:  # some receivers have devices past their max # devices
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
            logger.warning("%s removed device %s", self, dev)
        else:
            if self.receiver_kind == "bolt":
                reply = self.write_register(_R.bolt_pairing, 0x03, key)
            else:
                reply = self.write_register(_R.receiver_pairing, 0x03, key)
            if reply:
                # invalidate the device
                dev.online = False
                dev.wpid = None
                if key in self._devices:
                    del self._devices[key]
                if logger.isEnabledFor(logging.INFO):
                    logger.info("%s unpaired device %s", self, dev)
            else:
                logger.error("%s failed to unpair device %s", self, dev)
                raise Exception("failed to unpair device %s: %s" % (dev.name, key))

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

    __repr__ = __str__

    __bool__ = __nonzero__ = lambda self: self.handle is not None
