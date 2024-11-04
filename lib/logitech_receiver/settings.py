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
from __future__ import annotations

import logging
import struct
import time

from enum import IntEnum
from typing import Any

from solaar.i18n import _

from . import common
from . import hidpp20_constants
from . import settings_validator
from .common import NamedInt

logger = logging.getLogger(__name__)

SENSITIVITY_IGNORE = "ignore"


class Kind(IntEnum):
    TOGGLE = 0x01
    CHOICE = 0x02
    RANGE = 0x04
    MAP_CHOICE = 0x0A
    MULTIPLE_TOGGLE = 0x10
    PACKED_RANGE = 0x20
    MULTIPLE_RANGE = 0x40
    HETERO = 0x80


class Setting:
    """A setting descriptor. Needs to be instantiated for each specific device."""

    name = label = description = ""
    feature = register = kind = None
    min_version = 0
    persist = True
    rw_options = {}
    validator_class = None
    validator_options = {}

    def __init__(self, device, rw, validator):
        self._device = device
        self._rw = rw
        self._validator = validator
        self.kind = getattr(self._validator, "kind", None)
        self._value = None

    @classmethod
    def build(cls, device):
        assert cls.feature or cls.register, "Settings require either a feature or a register"
        rw_class = cls.rw_class if hasattr(cls, "rw_class") else FeatureRW if cls.feature else RegisterRW
        rw = rw_class(cls.feature if cls.feature else cls.register, **cls.rw_options)
        p = device.protocol
        if p == 1.0:  # HID++ 1.0 devices do not support features
            assert rw.kind == RegisterRW.kind
        elif p >= 2.0:  # HID++ 2.0 devices do not support registers
            assert rw.kind == FeatureRW.kind
        validator_class = cls.validator_class
        validator = validator_class.build(cls, device, **cls.validator_options)
        if validator:
            assert cls.kind is None or cls.kind & validator.kind != 0
            return cls(device, rw, validator)

    def val_to_string(self, value):
        return self._validator.to_string(value)

    @property
    def choices(self):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")

        return self._validator.choices if self._validator and self._validator.kind & Kind.CHOICE else None

    @property
    def range(self):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")

        if self._validator.kind == Kind.RANGE:
            return self._validator.min_value, self._validator.max_value

    def _pre_read(self, cached, key=None):
        if self.persist and self._value is None and getattr(self._device, "persister", None):
            # We haven't read a value from the device yet,
            # maybe we have something in the configuration.
            self._value = self._device.persister.get(self.name)
        if cached and self._value is not None:
            if getattr(self._device, "persister", None) and self.name not in self._device.persister:
                # If this is a new device (or a new setting for an old device),
                # make sure to save its current value for the next time.
                self._device.persister[self.name] = self._value if self.persist else None

    def read(self, cached=True):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")

        self._pre_read(cached)
        if cached and self._value is not None:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: cached value %r on %s", self.name, self._value, self._device)
            return self._value

        if self._device.online:
            reply = self._rw.read(self._device)
            if reply:
                self._value = self._validator.validate_read(reply)
            if self._value is not None and self._device.persister and self.name not in self._device.persister:
                # Don't update the persister if it already has a value,
                # otherwise the first read might overwrite the value we wanted.
                self._device.persister[self.name] = self._value if self.persist else None
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: read value %r on %s", self.name, self._value, self._device)
            return self._value

    def _pre_write(self, save=True):
        # Remember the value we're trying to set, even if the write fails.
        # This way even if the device is offline or some other error occurs,
        # the last value we've tried to write is remembered in the configuration.
        if self._device.persister and save:
            self._device.persister[self.name] = self._value if self.persist else None

    def update(self, value, save=True):
        self._value = value
        self._pre_write(save)

    def write(self, value, save=True):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        assert value is not None

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: write %r to %s", self.name, value, self._device)

        if self._device.online:
            if self._value != value:
                self.update(value, save)

            current_value = None
            if self._validator.needs_current_value:
                # the _validator needs the current value, possibly to merge flag values
                current_value = self._rw.read(self._device)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("%s: current value %r on %s", self.name, current_value, self._device)

            data_bytes = self._validator.prepare_write(value, current_value)
            if data_bytes is not None:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("%s: prepare write(%s) => %r", self.name, value, data_bytes)

                reply = self._rw.write(self._device, data_bytes)
                if not reply:
                    # tell whomever is calling that the write failed
                    return None

            return value

    def acceptable(self, args, current):
        return self._validator.acceptable(args, current) if self._validator else None

    def compare(self, args, current):
        return self._validator.compare(args, current) if self._validator else None

    def apply(self):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: apply (%s)", self.name, self._device)
        try:
            value = self.read(self.persist)  # Don't use persisted value if setting doesn't persist
            if self.persist and value is not None:  # If setting doesn't persist no need to write value just read
                self.write(value, save=False)
        except Exception as e:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("%s: error applying %s so ignore it (%s): %s", self.name, self._value, self._device, repr(e))

    def __str__(self):
        if hasattr(self, "_value"):
            assert hasattr(self, "_device")
            return "<Setting([%s:%s] %s:%s=%s)>" % (
                self._rw.kind,
                self._validator.kind if self._validator else None,
                self._device.codename,
                self.name,
                self._value,
            )
        return f"<Setting([{self._rw.kind}:{self._validator.kind if self._validator else None}] {self.name})>"

    __repr__ = __str__


class Settings(Setting):
    """A setting descriptor for multiple choices, being a map from keys to values.
    Needs to be instantiated for each specific device."""

    def read(self, cached=True):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: settings read %r from %s", self.name, self._value, self._device)

        self._pre_read(cached)

        if cached and self._value is not None:
            return self._value

        if self._device.online:
            reply_map = {}
            for key in self._validator.choices:
                reply = self._rw.read(self._device, key)
                if reply:
                    reply_map[int(key)] = self._validator.validate_read(reply, key)
            self._value = reply_map
            if getattr(self._device, "persister", None) and self.name not in self._device.persister:
                # Don't update the persister if it already has a value,
                # otherwise the first read might overwrite the value we wanted.
                self._device.persister[self.name] = self._value if self.persist else None
            return self._value

    def read_key(self, key, cached=True):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        assert key is not None
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: settings read %r key %r from %s", self.name, self._value, key, self._device)

        self._pre_read(cached)
        if cached and self._value is not None:
            return self._value[int(key)]

        if self._device.online:
            reply = self._rw.read(self._device, key)
            if reply:
                self._value[int(key)] = self._validator.validate_read(reply, key)
            if getattr(self._device, "persister", None) and self.name not in self._device.persister:
                self._device.persister[self.name] = self._value if self.persist else None
            return self._value[int(key)]

    def write(self, map, save=True):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        assert map is not None

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: settings write %r to %s", self.name, map, self._device)

        if self._device.online:
            self.update(map, save)
            for key, value in map.items():
                data_bytes = self._validator.prepare_write(int(key), value)
                if data_bytes is not None:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("%s: settings prepare map write(%s,%s) => %r", self.name, key, value, data_bytes)
                    reply = self._rw.write(self._device, int(key), data_bytes)
                    if not reply:
                        return None
            return map

    def update_key_value(self, key, value, save=True):
        self._value[int(key)] = value
        self._pre_write(save)

    def write_key_value(self, key, value, save=True) -> Any | None:
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        assert key is not None
        assert value is not None

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: settings write key %r value %r to %s", self.name, key, value, self._device)

        if self._device.online:
            if not self._value:
                self.read()
            try:
                data_bytes = self._validator.prepare_write(int(key), value)
                # always need to write to configuration because dictionary is shared and could have changed
                self.update_key_value(key, value, save)
            except ValueError:
                data_bytes = value = None
            if data_bytes is not None:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("%s: settings prepare key value write(%s,%s) => %r", self.name, key, value, data_bytes)
                reply = self._rw.write(self._device, int(key), data_bytes)
                if not reply:
                    return None
            return value


class LongSettings(Setting):
    """A setting descriptor for multiple choices, being a map from keys to values.
    Allows multiple write requests, if the options don't fit in 16 bytes.
    The validator must return a list.
    Needs to be instantiated for each specific device."""

    def read(self, cached=True):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: settings read %r from %s", self.name, self._value, self._device)

        self._pre_read(cached)

        if cached and self._value is not None:
            return self._value

        if self._device.online:
            reply_map = {}
            # Reading one item at a time. This can probably be optimised
            for item in self._validator.items:
                r = self._validator.prepare_read_item(item)
                reply = self._rw.read(self._device, r)
                if reply:
                    reply_map[int(item)] = self._validator.validate_read_item(reply, item)
            self._value = reply_map
            if getattr(self._device, "persister", None) and self.name not in self._device.persister:
                # Don't update the persister if it already has a value,
                # otherwise the first read might overwrite the value we wanted.
                self._device.persister[self.name] = self._value if self.persist else None
            return self._value

    def read_item(self, item, cached=True):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        assert item is not None
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: settings read %r item %r from %s", self.name, self._value, item, self._device)

        self._pre_read(cached)
        if cached and self._value is not None:
            return self._value[int(item)]

        if self._device.online:
            r = self._validator.prepare_read_item(item)
            reply = self._rw.read(self._device, r)
            if reply:
                self._value[int(item)] = self._validator.validate_read_item(reply, item)
            if getattr(self._device, "persister", None) and self.name not in self._device.persister:
                self._device.persister[self.name] = self._value if self.persist else None
            return self._value[int(item)]

    def write(self, map, save=True):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        assert map is not None

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: long settings write %r to %s", self.name, map, self._device)
        if self._device.online:
            self.update(map, save)
            for item, value in map.items():
                data_bytes_list = self._validator.prepare_write(self._value)
                if data_bytes_list is not None:
                    for data_bytes in data_bytes_list:
                        if data_bytes is not None:
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug("%s: settings prepare map write(%s,%s) => %r", self.name, item, value, data_bytes)
                            reply = self._rw.write(self._device, data_bytes)
                            if not reply:
                                return None
            return map

    def update_key_value(self, key, value, save=True):
        self._value[int(key)] = value
        self._pre_write(save)

    def write_key_value(self, item, value, save=True):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        assert item is not None
        assert value is not None

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: long settings write item %r value %r to %s", self.name, item, value, self._device)

        if self._device.online:
            if not self._value:
                self.read()
            data_bytes = self._validator.prepare_write_item(item, value)
            self.update_key_value(item, value, save)
            if data_bytes is not None:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("%s: settings prepare item value write(%s,%s) => %r", self.name, item, value, data_bytes)
                reply = self._rw.write(self._device, data_bytes)
                if not reply:
                    return None
            return value


class BitFieldSetting(Setting):
    """A setting descriptor for a set of choices represented by one bit each, being a map from options to booleans.
    Needs to be instantiated for each specific device."""

    def read(self, cached=True):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: settings read %r from %s", self.name, self._value, self._device)

        self._pre_read(cached)

        if cached and self._value is not None:
            return self._value

        if self._device.online:
            reply_map = {}
            reply = self._do_read()
            if reply:
                reply_map = self._validator.validate_read(reply)
            self._value = reply_map
            if getattr(self._device, "persister", None) and self.name not in self._device.persister:
                # Don't update the persister if it already has a value,
                # otherwise the first read might overwrite the value we wanted.
                self._device.persister[self.name] = self._value if self.persist else None
            return self._value

    def _do_read(self):
        return self._rw.read(self._device)

    def read_key(self, key, cached=True):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        assert key is not None
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: settings read %r key %r from %s", self.name, self._value, key, self._device)

        self._pre_read(cached)

        if cached and self._value is not None:
            return self._value[int(key)]

        if self._device.online:
            reply = self._do_read_key(key)
            if reply:
                self._value = self._validator.validate_read(reply)
            if getattr(self._device, "persister", None) and self.name not in self._device.persister:
                self._device.persister[self.name] = self._value if self.persist else None
            return self._value[int(key)]

    def _do_read_key(self, key):
        return self._rw.read(self._device, key)

    def write(self, map, save=True):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        assert map is not None

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: bit field settings write %r to %s", self.name, map, self._device)
        if self._device.online:
            self.update(map, save)
            data_bytes = self._validator.prepare_write(self._value)
            if data_bytes is not None:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("%s: settings prepare map write(%s) => %r", self.name, self._value, data_bytes)
                # if prepare_write returns a list, write one item at a time
                seq = data_bytes if isinstance(data_bytes, list) else [data_bytes]
                for b in seq:
                    reply = self._rw.write(self._device, b)
                    if not reply:
                        return None
            return map

    def update_key_value(self, key, value, save=True):
        self._value[int(key)] = value
        self._pre_write(save)

    def write_key_value(self, key, value, save=True):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        assert key is not None
        assert value is not None

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: bit field settings write key %r value %r to %s", self.name, key, value, self._device)

        if self._device.online:
            if not self._value:
                self.read()
            value = bool(value)
            self.update_key_value(key, value, save)

            data_bytes = self._validator.prepare_write(self._value)
            if data_bytes is not None:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("%s: settings prepare key value write(%s,%s) => %r", self.name, key, str(value), data_bytes)
                # if prepare_write returns a list, write one item at a time
                seq = data_bytes if isinstance(data_bytes, list) else [data_bytes]
                for b in seq:
                    reply = self._rw.write(self._device, b)
                    if not reply:
                        return None

            return value


class BitFieldWithOffsetAndMaskSetting(BitFieldSetting):
    """A setting descriptor for a set of choices represented by one bit each,
    each one having an offset, being a map from options to booleans.
    Needs to be instantiated for each specific device."""

    def _do_read(self):
        return {r: self._rw.read(self._device, r) for r in self._validator.prepare_read()}

    def _do_read_key(self, key):
        r = self._validator.prepare_read_key(key)
        return {r: self._rw.read(self._device, r)}


class RangeFieldSetting(Setting):
    """A setting descriptor for a set of choices represented by one field each, with map from option names to range(0,n).
    Needs to be instantiated for each specific device."""

    def read(self, cached=True):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: settings read %r from %s", self.name, self._value, self._device)
        self._pre_read(cached)
        if cached and self._value is not None:
            return self._value
        if self._device.online:
            reply_map = {}
            reply = self._do_read()
            if reply:
                reply_map = self._validator.validate_read(reply)
            self._value = reply_map
            if getattr(self._device, "persister", None) and self.name not in self._device.persister:
                # Don't update the persister if it already has a value,
                # otherwise the first read might overwrite the value we wanted.
                self._device.persister[self.name] = self._value if self.persist else None
            return self._value

    def _do_read(self):
        return self._rw.read(self._device)

    def read_key(self, key, cached=True):
        return self.read(cached)[int(key)]

    def write(self, map, save=True):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        assert map is not None
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: range field setting write %r to %s", self.name, map, self._device)
        if self._device.online:
            self.update(map, save)
            data_bytes = self._validator.prepare_write(self._value)
            if data_bytes is not None:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("%s: range field setting prepare map write(%s) => %r", self.name, self._value, data_bytes)
                reply = self._rw.write(self._device, data_bytes)
                if not reply:
                    return None
            elif logger.isEnabledFor(logging.WARNING):
                logger.warning("%s: range field setting no data to write", self.name)
            return map

    def write_key_value(self, key, value, save=True):
        assert key is not None
        assert value is not None
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: range field setting write key %r value %r to %s", self.name, key, value, self._device)
        if self._device.online:
            if not self._value:
                self.read()
            map = self._value
            map[int(key)] = value
            self.write(map, save)
            return value


#
# read/write low-level operators
#


class RegisterRW:
    __slots__ = ("register",)

    kind = NamedInt(0x01, _("register"))

    def __init__(self, register: int):
        assert isinstance(register, int)
        self.register = register

    def read(self, device):
        return device.read_register(self.register)

    def write(self, device, data_bytes):
        return device.write_register(self.register, data_bytes)


class FeatureRW:
    kind = NamedInt(0x02, _("feature"))
    default_read_fnid = 0x00
    default_write_fnid = 0x10

    def __init__(
        self,
        feature: hidpp20_constants.SupportedFeature,
        read_fnid=0x00,
        write_fnid=0x10,
        prefix=b"",
        suffix=b"",
        read_prefix=b"",
        no_reply=False,
    ):
        assert isinstance(feature, hidpp20_constants.SupportedFeature)
        self.feature = feature
        self.read_fnid = read_fnid
        self.write_fnid = write_fnid
        self.no_reply = no_reply
        self.prefix = prefix
        self.suffix = suffix
        self.read_prefix = read_prefix

    def read(self, device, data_bytes=b""):
        assert self.feature is not None
        return device.feature_request(self.feature, self.read_fnid, self.prefix, self.read_prefix, data_bytes)

    def write(self, device, data_bytes):
        assert self.feature is not None
        write_bytes = self.prefix + (data_bytes.to_bytes(1) if isinstance(data_bytes, int) else data_bytes) + self.suffix
        reply = device.feature_request(self.feature, self.write_fnid, write_bytes, no_reply=self.no_reply)
        return reply if not self.no_reply else True


class FeatureRWMap(FeatureRW):
    kind = NamedInt(0x02, _("feature"))
    default_read_fnid = 0x00
    default_write_fnid = 0x10
    default_key_byte_count = 1

    def __init__(
        self,
        feature: hidpp20_constants.SupportedFeature,
        read_fnid=default_read_fnid,
        write_fnid=default_write_fnid,
        key_byte_count=default_key_byte_count,
        no_reply=False,
    ):
        assert isinstance(feature, hidpp20_constants.SupportedFeature)
        self.feature = feature
        self.read_fnid = read_fnid
        self.write_fnid = write_fnid
        self.key_byte_count = key_byte_count
        self.no_reply = no_reply

    def read(self, device, key):
        assert self.feature is not None
        key_bytes = common.int2bytes(key, self.key_byte_count)
        return device.feature_request(self.feature, self.read_fnid, key_bytes)

    def write(self, device, key, data_bytes):
        assert self.feature is not None
        key_bytes = common.int2bytes(key, self.key_byte_count)
        reply = device.feature_request(self.feature, self.write_fnid, key_bytes, data_bytes, no_reply=self.no_reply)
        return reply if not self.no_reply else True


class ActionSettingRW:
    """Special RW class for settings that turn on and off special processing when a key or button is depressed"""

    def __init__(self, feature, name="", divert_setting_name="divert-keys"):
        self.feature = feature  # not used?
        self.name = name
        self.divert_setting_name = divert_setting_name
        self.kind = FeatureRW.kind  # pretend to be FeatureRW as required for HID++ 2.0 devices
        self.device = None
        self.key = None
        self.active = False
        self.pressed = False

    def activate_action(self):  # action to take when setting is activated (write non-false)
        pass

    def deactivate_action(self):  # action to take when setting is deactivated (write false)
        pass

    def press_action(self):  # action to take when key is pressed
        pass

    def release_action(self):  # action to take when key is released
        pass

    def move_action(self, dx, dy):  # action to take when mouse is moved while key is down
        pass

    def key_action(self, key):  # acction to take when some other diverted key is pressed
        pass

    def read(self, device):  # need to return bytes, as if read from device
        return common.int2bytes(self.key.key, 2) if self.active and self.key else b"\x00\x00"

    def write(self, device, data_bytes):
        def handler(device, n):  # Called on notification events from the device
            if (
                n.sub_id < 0x40
                and device.features.get_feature(n.sub_id) == hidpp20_constants.SupportedFeature.REPROG_CONTROLS_V4
            ):
                if n.address == 0x00:
                    cids = struct.unpack("!HHHH", n.data[:8])
                    if not self.pressed and int(self.key.key) in cids:  # trigger key pressed
                        self.pressed = True
                        self.press_action()
                    elif self.pressed:
                        if int(self.key.key) not in cids:  # trigger key released
                            self.pressed = False
                            self.release_action()
                        else:
                            for key in cids:
                                if key and not key == self.key.key:  # some other diverted key pressed
                                    self.key_action(key)
                elif n.address == 0x10:
                    if self.pressed:
                        dx, dy = struct.unpack("!hh", n.data[:4])
                        self.move_action(dx, dy)

        divertSetting = next(filter(lambda s: s.name == self.divert_setting_name, device.settings), None)
        if divertSetting is None:
            logger.warning("setting %s not found on %s", self.divert_setting_name, device.name)
            return None
        self.device = device
        key = common.bytes2int(data_bytes)
        if key:  # Enable
            self.key = next((k for k in device.keys if k.key == key), None)
            if self.key:
                self.active = True
                if divertSetting:
                    divertSetting.write_key_value(int(self.key.key), 1)
                    if self.device.setting_callback:
                        self.device.setting_callback(device, type(divertSetting), [self.key.key, 1])
                device.add_notification_handler(self.name, handler)
                self.activate_action()
            else:
                logger.error("cannot enable %s on %s for key %s", self.name, device, key)
        else:  # Disable
            if self.active:
                self.active = False
                if divertSetting:
                    divertSetting.write_key_value(int(self.key.key), 0)
                    if self.device.setting_callback:
                        self.device.setting_callback(device, type(divertSetting), [self.key.key, 0])
                try:
                    device.remove_notification_handler(self.name)
                except Exception:
                    if logger.isEnabledFor(logging.WARNING):
                        logger.warning("cannot disable %s on %s", self.name, device)
                self.deactivate_action()
        return data_bytes


class RawXYProcessing:
    """Special class for processing RawXY action messages initiated by pressing a key with rawXY diversion capability"""

    def __init__(self, device, name=""):
        self.device = device
        self.name = name
        self.keys = []  # the keys that can initiate processing
        self.initiating_key = None  # the key that did initiate processing
        self.active = False
        self.feature_offset = device.features[hidpp20_constants.SupportedFeature.REPROG_CONTROLS_V4]
        assert self.feature_offset is not False

    def handler(self, device, n):  # Called on notification events from the device
        if n.sub_id < 0x40 and device.features.get_feature(n.sub_id) == hidpp20_constants.SupportedFeature.REPROG_CONTROLS_V4:
            if n.address == 0x00:
                cids = struct.unpack("!HHHH", n.data[:8])
                ## generalize to list of keys
                if not self.initiating_key:  # no initiating key pressed
                    for k in self.keys:
                        if int(k.key) in cids:  # initiating key that was pressed
                            self.initiating_key = k
                    if self.initiating_key:
                        self.press_action(self.initiating_key)
                else:
                    if int(self.initiating_key.key) not in cids:  # initiating key released
                        self.initiating_key = None
                        self.release_action()
                    else:
                        for key in cids:
                            if key and key != self.initiating_key.key:
                                self.key_action(key)
            elif n.address == 0x10:
                if self.initiating_key:
                    dx, dy = struct.unpack("!hh", n.data[:4])
                    self.move_action(dx, dy)

    def start(self, key):
        device_key = next((k for k in self.device.keys if k.key == key), None)
        if device_key:
            self.keys.append(device_key)
            if not self.active:
                self.active = True
                self.activate_action()
                self.device.add_notification_handler(self.name, self.handler)
            device_key.set_rawXY_reporting(True)

    def stop(self, key):  # only stop if this is the active key
        if self.active:
            processing_key = next((k for k in self.keys if k.key == key), None)
            if processing_key:
                processing_key.set_rawXY_reporting(False)
                self.keys.remove(processing_key)
            if not self.keys:
                try:
                    self.device.remove_notification_handler(self.name)
                except Exception:
                    if logger.isEnabledFor(logging.WARNING):
                        logger.warning("cannot disable %s on %s", self.name, self.device)
                self.deactivate_action()
                self.active = False

    def activate_action(self):  # action to take when processing is activated
        pass

    def deactivate_action(self):  # action to take when processing is deactivated
        pass

    def press_action(self, key):  # action to take when an initiating key is pressed
        pass

    def release_action(self):  # action to take when key is released
        pass

    def move_action(self, dx, dy):  # action to take when mouse is moved while key is down
        pass

    def key_action(self, key):  # acction to take when some other diverted key is pressed
        pass


def apply_all_settings(device):
    if device.features and hidpp20_constants.SupportedFeature.HIRES_WHEEL in device.features:
        time.sleep(0.2)  # delay to try to get out of race condition with Linux HID++ driver
    persister = getattr(device, "persister", None)
    sensitives = persister.get("_sensitive", {}) if persister else {}
    for s in device.settings:
        ignore = sensitives.get(s.name, False)
        if ignore != SENSITIVITY_IGNORE:
            s.apply()


Setting.validator_class = settings_validator.BooleanValidator
