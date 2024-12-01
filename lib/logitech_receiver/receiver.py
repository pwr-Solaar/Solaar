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

from __future__ import annotations

import errno
import logging
import time
import typing

from dataclasses import dataclass
from typing import Callable
from typing import Optional
from typing import Protocol

from solaar.i18n import _
from solaar.i18n import ngettext

from . import exceptions
from . import hidpp10
from . import hidpp10_constants
from .common import Alert
from .common import Notification
from .device import Device
from .hidpp10_constants import InfoSubRegisters
from .hidpp10_constants import NotificationFlag
from .hidpp10_constants import Registers

if typing.TYPE_CHECKING:
    from logitech_receiver import common

    from .base import HIDPPNotification

logger = logging.getLogger(__name__)

_hidpp10 = hidpp10.Hidpp10()


class LowLevelInterface(Protocol):
    def open_path(self, path):
        ...

    def find_paired_node_wpid(self, receiver_path: str, index: int):
        ...

    def ping(self, handle, number, long_message=False):
        ...

    def request(self, handle, devnumber, request_id, *params, **kwargs):
        ...

    def close(self, handle):
        ...


@dataclass
class Pairing:
    """Information about the current or most recent pairing"""

    lock_open: bool = False
    discovering: bool = False
    counter: Optional[int] = None
    device_address: Optional[bytes] = None
    device_authentication: Optional[int] = None
    device_kind: Optional[int] = None
    device_name: Optional[str] = None
    device_passkey: Optional[str] = None
    new_device: Optional[Device] = None
    error: Optional[any] = None


def extract_serial(response: bytes) -> str:
    """Extracts serial number from receiver response."""
    return response.hex().upper()


def extract_max_devices(response: bytes) -> int:
    """Extracts maximum number of supported devices from response."""
    max_devices = response[6]
    return int(max_devices)


def extract_remaining_pairings(response: bytes) -> int:
    ps = ord(response[2:3])
    remaining_pairings = ps - 5 if ps >= 5 else -1
    return int(remaining_pairings)


def extract_codename(response: bytes) -> str:
    codename = response[2 : 2 + ord(response[1:2])]
    return codename.decode("ascii")


def extract_power_switch_location(response: bytes) -> str:
    """Extracts power switch location from response."""
    index = response[9] & 0x0F
    return hidpp10_constants.PowerSwitchLocation(index).name.lower()


def extract_connection_count(response: bytes) -> int:
    """Extract connection count from receiver response."""
    return ord(response[1:2])


def extract_wpid(response: bytes) -> str:
    """Extract wpid from receiver response."""
    return response.hex().upper()


def extract_polling_rate(response: bytes) -> int:
    """Returns polling rate in milliseconds."""
    return int(response[2])


def extract_device_kind(response: int) -> str:
    return hidpp10_constants.DEVICE_KIND[response]


class Receiver:
    """A generic Receiver instance, mostly implementing the interface used on Unifying, Nano, and LightSpeed receivers"
    The paired devices are available through the sequence interface.
    """

    read_register: Callable = hidpp10.read_register
    write_register: Callable = hidpp10.write_register
    number = 0xFF
    kind = None

    def __init__(
        self,
        low_level: LowLevelInterface,
        receiver_kind,
        product_info,
        handle,
        path,
        product_id,
        setting_callback=None,
    ):
        assert handle
        self.low_level = low_level
        self.isDevice = False  # some devices act as receiver so we need a property to distinguish them
        self.handle = handle
        self.path = path
        self.product_id = product_id
        self.setting_callback = setting_callback  # for changes to settings
        self.status_callback = None  # for changes to other potentially visible aspects
        self.receiver_kind = receiver_kind
        self.serial = None
        self.max_devices = None
        self._firmware = None
        self._remaining_pairings = None
        self._devices = {}
        self.name = product_info.get("name", "Receiver")
        self.may_unpair = product_info.get("may_unpair", False)
        self.re_pairs = product_info.get("re_pairs", False)
        self.notification_flags = None
        self.pairing = Pairing()
        self.initialize(product_info)
        hidpp10.set_configuration_pending_flags(self, 0xFF)

    def initialize(self, product_info: dict):
        # read the receiver information subregister, so we can find out max_devices
        serial_reply = self.read_register(Registers.RECEIVER_INFO, InfoSubRegisters.RECEIVER_INFORMATION)
        if serial_reply:
            self.serial = extract_serial(serial_reply[1:5])
            self.max_devices = extract_max_devices(serial_reply)
            if not (1 <= self.max_devices <= 6):
                self.max_devices = product_info.get("max_devices", 1)
        else:  # handle receivers that don't have a serial number specially (i.e., c534)
            self.serial = None
            self.max_devices = product_info.get("max_devices", 1)

    def close(self):
        handle, self.handle = self.handle, None
        for _n, d in self._devices.items():
            if d:
                d.close()
        self._devices.clear()
        return handle and self.low_level.close(handle)

    def __del__(self):
        self.close()

    def changed(self, alert=Alert.NOTIFICATION, reason=None):
        """The status of the device had changed, so invoke the status callback"""
        if self.status_callback is not None:
            self.status_callback(self, alert=alert, reason=reason)

    @property
    def firmware(self) -> tuple[common.FirmwareInfo]:
        if self._firmware is None and self.handle:
            self._firmware = _hidpp10.get_firmware(self)
        return self._firmware

    # how many pairings remain (None for unknown, -1 for unlimited)
    def remaining_pairings(self, cache=True):
        if self._remaining_pairings is None or not cache:
            ps = self.read_register(Registers.RECEIVER_CONNECTION)
            if ps is not None:
                self._remaining_pairings = extract_remaining_pairings(ps)
        return self._remaining_pairings

    def enable_connection_notifications(self, enable=True):
        """Enable or disable device (dis)connection notifications on this
        receiver."""
        if not self.handle:
            return False

        if enable:
            set_flag_bits = NotificationFlag.WIRELESS | NotificationFlag.SOFTWARE_PRESENT
        else:
            set_flag_bits = 0
        ok = _hidpp10.set_notification_flags(self, set_flag_bits)
        if ok is None:
            logger.warning("%s: failed to %s receiver notifications", self, "enable" if enable else "disable")
            return None

        flag_bits = _hidpp10.get_notification_flags(self)
        if flag_bits is None:
            flag_names = None
        else:
            flag_names = hidpp10_constants.NotificationFlag.flag_names(flag_bits)
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: receiver notifications %s => %s", self, "enabled" if enable else "disabled", flag_names)
        return flag_bits

    def device_codename(self, n):
        codename = self.read_register(Registers.RECEIVER_INFO, InfoSubRegisters.DEVICE_NAME + n - 1)
        if codename:
            return extract_codename(codename)

    def notify_devices(self):
        """Scan all devices."""
        if self.handle:
            if not self.write_register(Registers.RECEIVER_CONNECTION, 0x02):
                logger.warning("%s: failed to trigger device link notifications", self)

    def notification_information(self, number, notification: HIDPPNotification) -> tuple[bool, bool, typing.Any, str]:
        """Extract information from unifying-style notification"""
        assert notification.address != 0x02
        online = not bool(notification.data[0] & 0x40)
        encrypted = bool(notification.data[0] & 0x20) or notification.address == 0x10
        kind = extract_device_kind(notification.data[0] & 0x0F)
        wpid = extract_wpid(notification.data[2:3] + notification.data[1:2])
        return online, encrypted, wpid, kind

    def device_pairing_information(self, n: int) -> dict:
        """Return information from pairing registers (and elsewhere when necessary)"""
        polling_rate = ""
        serial = None
        power_switch = "(unknown)"
        pair_info = self.read_register(Registers.RECEIVER_INFO, InfoSubRegisters.PAIRING_INFORMATION + n - 1)
        if pair_info:  # a receiver that uses Unifying-style pairing registers
            wpid = extract_wpid(pair_info[3:5])
            kind = extract_device_kind(pair_info[7] & 0x0F)
            polling_rate_ms = extract_polling_rate(pair_info)
            polling_rate = f"{polling_rate_ms}ms"
        elif not self.receiver_kind == "unifying":  # may be an old Nano receiver
            device_info = self.read_register(Registers.RECEIVER_INFO, 0x04)  # undocumented
            if device_info:
                logger.warning("using undocumented register for device wpid")
                wpid = extract_wpid(device_info[3:5])
                kind = extract_device_kind(0x00)  # unknown kind
            else:
                raise exceptions.NoSuchDevice(number=n, receiver=self, error="read pairing information - non-unifying")
        else:
            raise exceptions.NoSuchDevice(number=n, receiver=self, error="read pairing information")
        pair_info = self.read_register(Registers.RECEIVER_INFO, InfoSubRegisters.EXTENDED_PAIRING_INFORMATION + n - 1)
        if pair_info:
            power_switch = extract_power_switch_location(pair_info)
            serial = extract_serial(pair_info[1:5])
        else:  # some Nano receivers?
            pair_info = self.read_register(0x2D5)  # undocumented and questionable
            if pair_info:
                logger.warning("using undocumented register for device serial number")
                serial = extract_serial(pair_info[1:5])
        return {"wpid": wpid, "kind": kind, "polling": polling_rate, "serial": serial, "power_switch": power_switch}

    def register_new_device(self, number, notification=None):
        if self._devices.get(number) is not None:
            raise IndexError(f"{self}: device number {int(number)} already registered")

        assert notification is None or notification.devnumber == number
        assert notification is None or notification.sub_id == Notification.DJ_PAIRING

        try:
            time.sleep(0.05)  # let receiver settle
            info = self.device_pairing_information(number)
            if notification is not None:
                online, _e, nwpid, nkind = self.notification_information(number, notification)
                if info["wpid"] is None:
                    info["wpid"] = nwpid
                elif nwpid is not None and info["wpid"] != nwpid:
                    logger.warning("mismatch on device WPID %s %s", info["wpid"], nwpid)
                if info["kind"] is None:
                    info["kind"] = nkind
                elif nkind is not None and info["kind"] != nkind:
                    logger.warning("mismatch on device kind %s %s", info["kind"], nkind)
            else:
                online = True
            dev = Device(self.low_level, self, number, online, pairing_info=info, setting_callback=self.setting_callback)
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
            reply = self.write_register(Registers.RECEIVER_PAIRING, action, device, timeout)
            if reply:
                return True
            logger.warning("%s: failed to %s the receiver lock", self, "close" if lock_closed else "open")

    def count(self):
        count = self.read_register(Registers.RECEIVER_CONNECTION)
        if count is None:
            return 0
        return extract_connection_count(count)

    def request(self, request_id, *params):
        if bool(self):
            return self.low_level.request(self.handle, 0xFF, request_id, *params)

    def reset_pairing(self):
        self.pairing = Pairing()

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
            reply = self._unpair_device_per_receiver(key)
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
                raise Exception(f"failed to unpair device {dev.name}: {key}")

    def _unpair_device_per_receiver(self, key):
        """Receiver specific unpairing."""
        return self.write_register(Registers.RECEIVER_PAIRING, 0x03, key)

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

    def status_string(self):
        count = len(self)
        return (
            _("No paired devices.")
            if count == 0
            else ngettext("%(count)s paired device.", "%(count)s paired devices.", count) % {"count": count}
        )

    def __str__(self):
        return "<%s(%s,%s%s)>" % (
            self.name.replace(" ", ""),
            self.path,
            "" if isinstance(self.handle, int) else "T",
            self.handle,
        )

    __repr__ = __str__

    __bool__ = __nonzero__ = lambda self: self.handle is not None


class BoltReceiver(Receiver):
    """Bolt receivers use a different pairing prototol and have different pairing registers"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize(self, product_info: dict):
        serial_reply = self.read_register(Registers.BOLT_UNIQUE_ID)
        self.serial = extract_serial(serial_reply)
        self.max_devices = product_info.get("max_devices", 1)

    def device_codename(self, n):
        codename = self.read_register(Registers.RECEIVER_INFO, InfoSubRegisters.BOLT_DEVICE_NAME + n, 0x01)
        if codename:
            codename = codename[3 : 3 + min(14, ord(codename[2:3]))]
            return codename.decode("ascii")

    def device_pairing_information(self, n: int) -> dict:
        pair_info = self.read_register(Registers.RECEIVER_INFO, InfoSubRegisters.BOLT_PAIRING_INFORMATION + n)
        if pair_info:
            wpid = extract_wpid(pair_info[3:4] + pair_info[2:3])
            kind = extract_device_kind(pair_info[1] & 0x0F)
            serial = extract_serial(pair_info[4:8])
            return {"wpid": wpid, "kind": kind, "polling": None, "serial": serial, "power_switch": "(unknown)"}
        else:
            raise exceptions.NoSuchDevice(number=n, receiver=self, error="can't read Bolt pairing register")

    def discover(self, cancel=False, timeout=30):
        """Discover Logitech Bolt devices."""
        if self.handle:
            action = 0x02 if cancel else 0x01
            reply = self.write_register(Registers.BOLT_DEVICE_DISCOVERY, timeout, action)
            if reply:
                return True
            logger.warning("%s: failed to %s device discovery", self, "cancel" if cancel else "start")

    def pair_device(self, pair=True, slot=0, address=b"\0\0\0\0\0\0", authentication=0x00, entropy=20):
        """Pair a Bolt device."""
        if self.handle:
            action = 0x01 if pair is True else 0x03 if pair is False else 0x02
            reply = self.write_register(Registers.BOLT_PAIRING, action, slot, address, authentication, entropy)
            if reply:
                return True
            logger.warning("%s: failed to %s device %s", self, "pair" if pair else "unpair", address)

    def _unpair_device_per_receiver(self, key):
        """Receiver specific unpairing."""
        return self.write_register(Registers.BOLT_PAIRING, 0x03, key)


class UnifyingReceiver(Receiver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class NanoReceiver(Receiver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class LightSpeedReceiver(Receiver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Ex100Receiver(Receiver):
    """A very old style receiver, somewhat different from newer receivers"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize(self, product_info: dict):
        self.serial = None
        self.max_devices = product_info.get("max_devices", 1)

    def notification_information(self, number, notification):
        """Extract information from 27Mz-style notification and device index"""
        assert notification.address == 0x02
        online = True
        encrypted = bool(notification.data[0] & 0x80)
        kind = extract_device_kind(_get_kind_from_index(self, number))
        wpid = extract_wpid("00" + notification.data[2:3])
        return online, encrypted, wpid, kind

    def device_pairing_information(self, number: int) -> dict:
        # extract WPID from udev path
        wpid = self.low_level.find_paired_node_wpid(self.path, number)
        if not wpid:
            logger.error("Unable to get wpid from udev for device %d of %s", number, self)
            raise exceptions.NoSuchDevice(number=number, receiver=self, error="Not present 27Mhz device")
        kind = extract_device_kind(_get_kind_from_index(self, number))
        return {"wpid": wpid, "kind": kind, "polling": "", "serial": None, "power_switch": "(unknown)"}


def _get_kind_from_index(receiver, index: int) -> int:
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
        logger.error("failed to calculate device kind for device %d of %s", index, receiver)
        raise exceptions.NoSuchDevice(number=index, receiver=receiver, error="Unknown 27Mhz device number")
    return kind


receiver_class_mapping = {
    "bolt": BoltReceiver,
    "unifying": UnifyingReceiver,
    "lightspeed": LightSpeedReceiver,
    "nano": NanoReceiver,
    "27Mhz": Ex100Receiver,
}


def create_receiver(low_level: LowLevelInterface, device_info, setting_callback=None) -> Optional[Receiver]:
    """Opens a Logitech Receiver found attached to the machine, by Linux device path."""

    try:
        handle = low_level.open_path(device_info.path)
        if handle:
            usb_id = device_info.product_id
            if isinstance(usb_id, str):
                usb_id = int(usb_id, 16)
            try:
                product_info = low_level.product_information(usb_id)
            except ValueError:
                product_info = {}
            kind = product_info.get("receiver_kind", "unknown")
            rclass = receiver_class_mapping.get(kind, Receiver)
            return rclass(
                low_level,
                kind,
                product_info,
                handle,
                device_info.path,
                device_info.product_id,
                setting_callback,
            )
    except OSError as e:
        logger.exception("open %s", device_info)
        if e.errno == errno.EACCES:
            raise
    except Exception:
        logger.exception("open %s", device_info)
