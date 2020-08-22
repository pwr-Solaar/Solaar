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

import math

from logging import DEBUG as _DEBUG
from logging import WARNING as _WARNING
from logging import getLogger

from . import hidpp20 as _hidpp20
from .common import NamedInt as _NamedInt
from .common import NamedInts as _NamedInts
from .common import bytes2int as _bytes2int
from .common import int2bytes as _int2bytes
from .common import unpack as _unpack
from .i18n import _

_log = getLogger(__name__)
del getLogger

#
#
#

SENSITIVITY_IGNORE = 'ignore'
KIND = _NamedInts(toggle=0x01, choice=0x02, range=0x04, map_choice=0x0A, multiple_toggle=0x10, multiple_range=0x40)


def bool_or_toggle(current, new):
    if isinstance(new, bool):
        return new
    try:
        return bool(int(new))
    except (TypeError, ValueError):
        new = str(new).lower()
    if new in ('true', 'yes', 'on', 't', 'y'):
        return True
    if new in ('false', 'no', 'off', 'f', 'n'):
        return False
    if new in ('~', 'toggle'):
        return not current
    return None


# moved first for dependency reasons
class Validator:
    @classmethod
    def build(cls, setting_class, device, **kwargs):
        return cls(**kwargs)

    @classmethod
    def to_string(cls, value):
        return (str(value))

    def compare(self, args, current):
        if len(args) != 1:
            return False
        return args[0] == current


class BooleanValidator(Validator):
    __slots__ = ('true_value', 'false_value', 'read_skip_byte_count', 'write_prefix_bytes', 'mask', 'needs_current_value')

    kind = KIND.toggle
    default_true = 0x01
    default_false = 0x00
    # mask specifies all the affected bits in the value
    default_mask = 0xFF

    def __init__(
        self,
        true_value=default_true,
        false_value=default_false,
        mask=default_mask,
        read_skip_byte_count=0,
        write_prefix_bytes=b''
    ):
        if isinstance(true_value, int):
            assert isinstance(false_value, int)
            if mask is None:
                mask = self.default_mask
            else:
                assert isinstance(mask, int)
            assert true_value & false_value == 0
            assert true_value & mask == true_value
            assert false_value & mask == false_value
            self.needs_current_value = (mask != self.default_mask)
        elif isinstance(true_value, bytes):
            if false_value is None or false_value == self.default_false:
                false_value = b'\x00' * len(true_value)
            else:
                assert isinstance(false_value, bytes)
            if mask is None or mask == self.default_mask:
                mask = b'\xFF' * len(true_value)
            else:
                assert isinstance(mask, bytes)
            assert len(mask) == len(true_value) == len(false_value)
            tv = _bytes2int(true_value)
            fv = _bytes2int(false_value)
            mv = _bytes2int(mask)
            assert tv != fv  # true and false might be something other than bit values
            assert tv & mv == tv
            assert fv & mv == fv
            self.needs_current_value = any(m != b'\xFF' for m in mask)
        else:
            raise Exception("invalid mask '%r', type %s" % (mask, type(mask)))

        self.true_value = true_value
        self.false_value = false_value
        self.mask = mask
        self.read_skip_byte_count = read_skip_byte_count
        self.write_prefix_bytes = write_prefix_bytes

    def validate_read(self, reply_bytes):
        reply_bytes = reply_bytes[self.read_skip_byte_count:]
        if isinstance(self.mask, int):
            reply_value = ord(reply_bytes[:1]) & self.mask
            if _log.isEnabledFor(_DEBUG):
                _log.debug('BooleanValidator: validate read %r => %02X', reply_bytes, reply_value)
            if reply_value == self.true_value:
                return True
            if reply_value == self.false_value:
                return False
            _log.warn(
                'BooleanValidator: reply %02X mismatched %02X/%02X/%02X', reply_value, self.true_value, self.false_value,
                self.mask
            )
            return False

        count = len(self.mask)
        mask = _bytes2int(self.mask)
        reply_value = _bytes2int(reply_bytes[:count]) & mask

        true_value = _bytes2int(self.true_value)
        if reply_value == true_value:
            return True

        false_value = _bytes2int(self.false_value)
        if reply_value == false_value:
            return False

        _log.warn('BooleanValidator: reply %r mismatched %r/%r/%r', reply_bytes, self.true_value, self.false_value, self.mask)
        return False

    def prepare_write(self, new_value, current_value=None):
        if new_value is None:
            new_value = False
        else:
            assert isinstance(new_value, bool), 'New value %s for boolean setting is not a boolean' % new_value

        to_write = self.true_value if new_value else self.false_value

        if isinstance(self.mask, int):
            if current_value is not None and self.needs_current_value:
                to_write |= ord(current_value[:1]) & (0xFF ^ self.mask)
            if current_value is not None and to_write == ord(current_value[:1]):
                return None
            to_write = bytes([to_write])
        else:
            to_write = bytearray(to_write)
            count = len(self.mask)
            for i in range(0, count):
                b = ord(to_write[i:i + 1])
                m = ord(self.mask[i:i + 1])
                assert b & m == b
                # b &= m
                if current_value is not None and self.needs_current_value:
                    b |= ord(current_value[i:i + 1]) & (0xFF ^ m)
                to_write[i] = b
            to_write = bytes(to_write)

            if current_value is not None and to_write == current_value[:len(to_write)]:
                return None

        if _log.isEnabledFor(_DEBUG):
            _log.debug('BooleanValidator: prepare_write(%s, %s) => %r', new_value, current_value, to_write)

        return self.write_prefix_bytes + to_write

    def acceptable(self, args, current):
        if len(args) != 1:
            return None
        val = bool_or_toggle(current, args[0])
        return [val] if val is not None else None


class Setting:
    """A setting descriptor. Needs to be instantiated for each specific device."""
    name = label = description = ''
    feature = register = kind = None
    persist = True
    rw_options = {}
    validator_class = BooleanValidator
    validator_options = {}

    def __init__(self, device, rw, validator):
        self._device = device
        self._rw = rw
        self._validator = validator
        self.kind = getattr(self._validator, 'kind', None)
        self._value = None

    @classmethod
    def build(cls, device):
        assert cls.feature or cls.register, 'Settings require either a feature or a register'
        rw_class = cls.rw_class if hasattr(cls, 'rw_class') else FeatureRW if cls.feature else RegisterRW
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
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')

        return self._validator.choices if self._validator and self._validator.kind & KIND.choice else None

    @property
    def range(self):
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')

        if self._validator.kind == KIND.range:
            return (self._validator.min_value, self._validator.max_value)

    def _pre_read(self, cached, key=None):
        if self.persist and self._value is None and getattr(self._device, 'persister', None):
            # We haven't read a value from the device yet,
            # maybe we have something in the configuration.
            self._value = self._device.persister.get(self.name)
        if cached and self._value is not None:
            if self.persist and getattr(self._device, 'persister', None) and self.name not in self._device.persister:
                # If this is a new device (or a new setting for an old device),
                # make sure to save its current value for the next time.
                self._device.persister[self.name] = self._value

    def read(self, cached=True):
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')
        if _log.isEnabledFor(_DEBUG):
            _log.debug('%s: settings read %r from %s', self.name, self._value, self._device)

        self._pre_read(cached)

        if cached and self._value is not None:
            return self._value

        if self._device.online:
            reply = self._rw.read(self._device)
            if reply:
                self._value = self._validator.validate_read(reply)
            if self.persist and self._device.persister and self.name not in self._device.persister:
                # Don't update the persister if it already has a value,
                # otherwise the first read might overwrite the value we wanted.
                self._device.persister[self.name] = self._value
            return self._value

    def _pre_write(self, save=True):
        # Remember the value we're trying to set, even if the write fails.
        # This way even if the device is offline or some other error occurs,
        # the last value we've tried to write is remembered in the configuration.
        if self.persist and self._device.persister and save:
            self._device.persister[self.name] = self._value

    def write(self, value, save=True):
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')
        assert value is not None

        if _log.isEnabledFor(_DEBUG):
            _log.debug('%s: settings write %r to %s', self.name, value, self._device)

        if self._device.online:
            if self._value != value:
                self._value = value
                self._pre_write(save)

            current_value = None
            if self._validator.needs_current_value:
                # the _validator needs the current value, possibly to merge flag values
                current_value = self._rw.read(self._device)

            data_bytes = self._validator.prepare_write(value, current_value)
            if data_bytes is not None:
                if _log.isEnabledFor(_DEBUG):
                    _log.debug('%s: settings prepare write(%s) => %r', self.name, value, data_bytes)

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
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')

        if _log.isEnabledFor(_DEBUG):
            _log.debug('%s: apply %s (%s)', self.name, self._value, self._device)

        value = self.read(self.persist)  # Don't use persisted value if setting doesn't persist
        if self.persist and value is not None:  # If setting doesn't persist no need to write value just read
            try:
                self.write(value, save=False)
            except Exception:
                if _log.isEnabledFor(_WARNING):
                    _log.warn('%s: error applying value %s so ignore it (%s)', self.name, self._value, self._device)

    def __str__(self):
        if hasattr(self, '_value'):
            assert hasattr(self, '_device')
            return '<Setting([%s:%s] %s:%s=%s)>' % (
                self._rw.kind, self._validator.kind if self._validator else None, self._device.codename, self.name, self._value
            )
        return '<Setting([%s:%s] %s)>' % (self._rw.kind, self._validator.kind if self._validator else None, self.name)

    __unicode__ = __repr__ = __str__


class Settings(Setting):
    """A setting descriptor for multiple choices, being a map from keys to values.
    Needs to be instantiated for each specific device."""
    def read(self, cached=True):
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')
        if _log.isEnabledFor(_DEBUG):
            _log.debug('%s: settings read %r from %s', self.name, self._value, self._device)

        self._pre_read(cached)

        if cached and self._value is not None:
            return self._value

        if self._device.online:
            reply_map = {}
            for key in self._validator.choices:
                reply = self._rw.read(self._device, key)
                if reply:
                    # keys are ints, because that is what the device uses,
                    # encoded into strings because JSON requires strings as keys
                    reply_map[str(int(key))] = self._validator.validate_read(reply, key)
            self._value = reply_map
            if self.persist and getattr(self._device, 'persister', None) and self.name not in self._device.persister:
                # Don't update the persister if it already has a value,
                # otherwise the first read might overwrite the value we wanted.
                self._device.persister[self.name] = self._value
            return self._value

    def read_key(self, key, cached=True):
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')
        assert key is not None
        if _log.isEnabledFor(_DEBUG):
            _log.debug('%s: settings read %r key %r from %s', self.name, self._value, key, self._device)

        self._pre_read(cached)
        if cached and self._value is not None:
            return self._value[str(int(key))]

        if self._device.online:
            reply = self._rw.read(self._device, key)
            if reply:
                self._value[str(int(key))] = self._validator.validate_read(reply, key)
            if self.persist and getattr(self._device, 'persister', None) and self.name not in self._device.persister:
                self._device.persister[self.name] = self._value
            return self._value[str(int(key))]

    def write(self, map, save=True):
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')
        assert map is not None

        if _log.isEnabledFor(_DEBUG):
            _log.debug('%s: settings write %r to %s', self.name, map, self._device)

        if self._device.online:
            self._value = map
            self._pre_write(save)
            for key, value in map.items():
                data_bytes = self._validator.prepare_write(int(key), value)
                if data_bytes is not None:
                    if _log.isEnabledFor(_DEBUG):
                        _log.debug('%s: settings prepare map write(%s,%s) => %r', self.name, key, value, data_bytes)
                    reply = self._rw.write(self._device, int(key), data_bytes)
                    if not reply:
                        return None
            return map

    def write_key_value(self, key, value):
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')
        assert key is not None
        assert value is not None

        if _log.isEnabledFor(_DEBUG):
            _log.debug('%s: settings write key %r value %r to %s', self.name, key, value, self._device)

        if self._device.online:
            if not self._value:
                self.read()
            try:
                data_bytes = self._validator.prepare_write(int(key), value)
                # always need to write to configuration because dictionary is shared and could have changed
                self._value[str(key)] = value
                self._pre_write()
            except ValueError:
                data_bytes = value = None
            if data_bytes is not None:
                if _log.isEnabledFor(_DEBUG):
                    _log.debug('%s: settings prepare key value write(%s,%s) => %r', self.name, key, value, data_bytes)
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
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')
        if _log.isEnabledFor(_DEBUG):
            _log.debug('%s: settings read %r from %s', self.name, self._value, self._device)

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
                    # keys are ints, because that is what the device uses,
                    # encoded into strings because JSON requires strings as keys
                    reply_map[str(int(item))] = self._validator.validate_read_item(reply, item)
            self._value = reply_map
            if self.persist and getattr(self._device, 'persister', None) and self.name not in self._device.persister:
                # Don't update the persister if it already has a value,
                # otherwise the first read might overwrite the value we wanted.
                self._device.persister[self.name] = self._value
            return self._value

    def read_item(self, item, cached=True):
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')
        assert item is not None
        if _log.isEnabledFor(_DEBUG):
            _log.debug('%s: settings read %r item %r from %s', self.name, self._value, item, self._device)

        self._pre_read(cached)
        if cached and self._value is not None:
            return self._value[str(int(item))]

        if self._device.online:
            r = self._validator.prepare_read_item(item)
            reply = self._rw.read(self._device, r)
            if reply:
                self._value[str(int(item))] = self._validator.validate_read_item(reply, item)
            if self.persist and getattr(self._device, 'persister', None) and self.name not in self._device.persister:
                self._device.persister[self.name] = self._value
            return self._value[str(int(item))]

    def write(self, map, save=True):
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')
        assert map is not None

        if _log.isEnabledFor(_DEBUG):
            _log.debug('%s: settings write %r to %s', self.name, map, self._device)
        if self._device.online:
            self._value = map
            self._pre_write(save)
            for item, value in map.items():
                data_bytes_list = self._validator.prepare_write(self._value)
                if data_bytes_list is not None:
                    for data_bytes in data_bytes_list:
                        if data_bytes is not None:
                            if _log.isEnabledFor(_DEBUG):
                                _log.debug('%s: settings prepare map write(%s,%s) => %r', self.name, item, value, data_bytes)
                            reply = self._rw.write(self._device, data_bytes)
                            if not reply:
                                return None
            return map

    def write_key_value(self, item, value):
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')
        assert item is not None
        assert value is not None

        if _log.isEnabledFor(_DEBUG):
            _log.debug('%s: settings write item %r value %r to %s', self.name, item, value, self._device)

        if self._device.online:
            if not self._value:
                self.read()
            data_bytes = self._validator.prepare_write_item(item, value)
            self._value[str(int(item))] = value
            self._pre_write()
            if data_bytes is not None:
                if _log.isEnabledFor(_DEBUG):
                    _log.debug('%s: settings prepare item value write(%s,%s) => %r', self.name, item, value, data_bytes)
                reply = self._rw.write(self._device, data_bytes)
                if not reply:
                    return None
            return value


class BitFieldSetting(Setting):
    """A setting descriptor for a set of choices represented by one bit each, being a map from options to booleans.
    Needs to be instantiated for each specific device."""
    def read(self, cached=True):
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')
        if _log.isEnabledFor(_DEBUG):
            _log.debug('%s: settings read %r from %s', self.name, self._value, self._device)

        self._pre_read(cached)

        if cached and self._value is not None:
            return self._value

        if self._device.online:
            reply_map = {}
            reply = self._do_read()
            if reply:
                # keys are ints, because that is what the device uses,
                # encoded into strings because JSON requires strings as keys
                reply_map = self._validator.validate_read(reply)
            self._value = reply_map
            if self.persist and getattr(self._device, 'persister', None) and self.name not in self._device.persister:
                # Don't update the persister if it already has a value,
                # otherwise the first read might overwrite the value we wanted.
                self._device.persister[self.name] = self._value
            return self._value

    def _do_read(self):
        return self._rw.read(self._device)

    def read_key(self, key, cached=True):
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')
        assert key is not None
        if _log.isEnabledFor(_DEBUG):
            _log.debug('%s: settings read %r key %r from %s', self.name, self._value, key, self._device)

        self._pre_read(cached)

        if cached and self._value is not None:
            return self._value[str(int(key))]

        if self._device.online:
            reply = self._do_read_key(key)
            if reply:
                self._value = self._validator.validate_read(reply)
            if self.persist and getattr(self._device, 'persister', None) and self.name not in self._device.persister:
                self._device.persister[self.name] = self._value
            return self._value[str(int(key))]

    def _do_read_key(self, key):
        return self._rw.read(self._device, key)

    def write(self, map, save=True):
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')
        assert map is not None

        if _log.isEnabledFor(_DEBUG):
            _log.debug('%s: settings write %r to %s', self.name, map, self._device)
        if self._device.online:
            self._value = map
            self._pre_write(save)
            data_bytes = self._validator.prepare_write(self._value)
            if data_bytes is not None:
                if _log.isEnabledFor(_DEBUG):
                    _log.debug('%s: settings prepare map write(%s) => %r', self.name, self._value, data_bytes)
                # if prepare_write returns a list, write one item at a time
                seq = data_bytes if isinstance(data_bytes, list) else [data_bytes]
                for b in seq:
                    reply = self._rw.write(self._device, b)
                    if not reply:
                        return None
            return map

    def write_key_value(self, key, value):
        assert hasattr(self, '_value')
        assert hasattr(self, '_device')
        assert key is not None
        assert value is not None

        if _log.isEnabledFor(_DEBUG):
            _log.debug('%s: settings write key %r value %r to %s', self.name, key, value, self._device)

        if self._device.online:
            if not self._value:
                self.read()
            value = bool(value)
            self._value[str(key)] = value
            self._pre_write()

            data_bytes = self._validator.prepare_write(self._value)
            if data_bytes is not None:
                if _log.isEnabledFor(_DEBUG):
                    _log.debug('%s: settings prepare key value write(%s,%s) => %r', self.name, key, str(value), data_bytes)
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


#
# read/write low-level operators
#


class RegisterRW:
    __slots__ = ('register', )

    kind = _NamedInt(0x01, _('register'))

    def __init__(self, register):
        assert isinstance(register, int)
        self.register = register

    def read(self, device):
        return device.read_register(self.register)

    def write(self, device, data_bytes):
        return device.write_register(self.register, data_bytes)


class FeatureRW:
    kind = _NamedInt(0x02, _('feature'))
    default_read_fnid = 0x00
    default_write_fnid = 0x10

    def __init__(
        self, feature, read_fnid=default_read_fnid, write_fnid=default_write_fnid, prefix=b'', suffix=b'', no_reply=False
    ):
        assert isinstance(feature, _NamedInt)
        self.feature = feature
        self.read_fnid = read_fnid
        self.write_fnid = write_fnid
        self.no_reply = no_reply
        self.prefix = prefix
        self.suffix = suffix

    def read(self, device, data_bytes=b''):
        assert self.feature is not None
        return device.feature_request(self.feature, self.read_fnid, self.prefix, data_bytes)

    def write(self, device, data_bytes):
        assert self.feature is not None
        reply = device.feature_request(
            self.feature, self.write_fnid, self.prefix, data_bytes, self.suffix, no_reply=self.no_reply
        )
        return reply if not self.no_reply else True


class FeatureRWMap(FeatureRW):
    kind = _NamedInt(0x02, _('feature'))
    default_read_fnid = 0x00
    default_write_fnid = 0x10
    default_key_byte_count = 1

    def __init__(
        self,
        feature,
        read_fnid=default_read_fnid,
        write_fnid=default_write_fnid,
        key_byte_count=default_key_byte_count,
        no_reply=False
    ):
        assert isinstance(feature, _NamedInt)
        self.feature = feature
        self.read_fnid = read_fnid
        self.write_fnid = write_fnid
        self.key_byte_count = key_byte_count
        self.no_reply = no_reply

    def read(self, device, key):
        assert self.feature is not None
        key_bytes = _int2bytes(key, self.key_byte_count)
        return device.feature_request(self.feature, self.read_fnid, key_bytes)

    def write(self, device, key, data_bytes):
        assert self.feature is not None
        key_bytes = _int2bytes(key, self.key_byte_count)
        reply = device.feature_request(self.feature, self.write_fnid, key_bytes, data_bytes, no_reply=self.no_reply)
        return reply if not self.no_reply else True


class BitFieldValidator(Validator):
    __slots__ = ('byte_count', 'options')

    kind = KIND.multiple_toggle

    def __init__(self, options, byte_count=None):
        assert (isinstance(options, list))
        self.options = options
        self.byte_count = (max(x.bit_length() for x in options) + 7) // 8
        if byte_count:
            assert (isinstance(byte_count, int) and byte_count >= self.byte_count)
            self.byte_count = byte_count

    def to_string(self, value):
        def element_to_string(key, val):
            k = next((k for k in self.options if int(key) == k), None)
            return str(k) + ':' + str(val) if k is not None else '?'

        return '{' + ', '.join([element_to_string(k, value[k]) for k in value]) + '}'

    def validate_read(self, reply_bytes):
        r = _bytes2int(reply_bytes[:self.byte_count])
        value = {str(int(k)): False for k in self.options}
        m = 1
        for _ignore in range(8 * self.byte_count):
            if m in self.options:
                value[str(int(m))] = bool(r & m)
            m <<= 1
        return value

    def prepare_write(self, new_value):
        assert (isinstance(new_value, dict))
        w = 0
        for k, v in new_value.items():
            if v:
                w |= int(k)
        return _int2bytes(w, self.byte_count)

    def get_options(self):
        return self.options

    def acceptable(self, args, current):
        if len(args) != 2:
            return None
        key = next((key for key in self.options if key == args[0]), None)
        if key is None:
            return None
        val = bool_or_toggle(current[str(int(key))], args[1])
        return None if val is None else [str(int(key)), val]

    def compare(self, args, current):
        if len(args) != 2:
            return False
        key = next((key for key in self.options if key == args[0]), None)
        if key is None:
            return False
        return args[1] == current[str(int(key))]


class BitFieldWithOffsetAndMaskValidator(Validator):
    __slots__ = ('byte_count', 'options', '_option_from_key', '_mask_from_offset', '_option_from_offset_mask')

    kind = KIND.multiple_toggle
    sep = 0x01

    def __init__(self, options, byte_count=None):
        assert (isinstance(options, list))
        # each element of options must have .offset and .mask,
        # and its int representation must be its id (not its index)
        self.options = options
        # to retrieve the options efficiently:
        self._option_from_key = {}
        self._mask_from_offset = {}
        self._option_from_offset_mask = {}
        for opt in options:
            self._option_from_key[int(opt)] = opt
            try:
                self._mask_from_offset[opt.offset] |= opt.mask
            except KeyError:
                self._mask_from_offset[opt.offset] = opt.mask
            try:
                mask_to_opt = self._option_from_offset_mask[opt.offset]
            except KeyError:
                mask_to_opt = {}
                self._option_from_offset_mask[opt.offset] = mask_to_opt
            mask_to_opt[opt.mask] = opt
        self.byte_count = (max(x.mask.bit_length() for x in options) + 7) // 8
        if byte_count:
            assert (isinstance(byte_count, int) and byte_count >= self.byte_count)
            self.byte_count = byte_count

    def prepare_read(self):
        r = []
        for offset, mask in self._mask_from_offset.items():
            b = (offset << (8 * (self.byte_count + 1)))
            b |= (self.sep << (8 * self.byte_count)) | mask
            r.append(_int2bytes(b, self.byte_count + 2))
        return r

    def prepare_read_key(self, key):
        option = self._option_from_key.get(key, None)
        if option is None:
            return None
        b = option.offset << (8 * (self.byte_count + 1))
        b |= (self.sep << (8 * self.byte_count)) | option.mask
        return _int2bytes(b, self.byte_count + 2)

    def validate_read(self, reply_bytes_dict):
        values = {str(int(k)): False for k in self.options}
        for query, b in reply_bytes_dict.items():
            offset = _bytes2int(query[0:1])
            b += (self.byte_count - len(b)) * b'\x00'
            value = _bytes2int(b[:self.byte_count])
            mask_to_opt = self._option_from_offset_mask.get(offset, {})
            m = 1
            for _ignore in range(8 * self.byte_count):
                if m in mask_to_opt:
                    values[str(int(mask_to_opt[m]))] = bool(value & m)
                m <<= 1
        return values

    def prepare_write(self, new_value):
        assert (isinstance(new_value, dict))
        w = {}
        for k, v in new_value.items():
            option = self._option_from_key[int(k)]
            if option.offset not in w:
                w[option.offset] = 0
            if v:
                w[option.offset] |= option.mask
        return [
            _int2bytes((offset << (8 * (2 * self.byte_count + 1)))
                       | (self.sep << (16 * self.byte_count))
                       | (self._mask_from_offset[offset] << (8 * self.byte_count))
                       | value, 2 * self.byte_count + 2) for offset, value in w.items()
        ]

    def get_options(self):
        return [int(opt) if isinstance(opt, int) else opt.as_int() for opt in self.options]

    def acceptable(self, args, current):
        if len(args) != 2:
            return None
        key = next((option.id for option in self.options if option.as_int() == args[0]), None)
        if key is None:
            return None
        val = bool_or_toggle(current[str(int(key))], args[1])
        return None if val is None else [str(int(key)), val]

    def compare(self, args, current):
        if len(args) != 2:
            return False
        key = next((option.id for option in self.options if option.as_int() == args[0]), None)
        if key is None:
            return False
        return args[1] == current[str(int(key))]


class ChoicesValidator(Validator):
    """Translates between NamedInts and a byte sequence.
    :param choices: a list of NamedInts
    :param byte_count: the size of the derived byte sequence. If None, it
    will be calculated from the choices."""
    kind = KIND.choice
    choices_universe = None  # the possible choices, or an empty sequence for anything
    choices_extra = None  # an extra choice, so as not to require extending a large NamedInts

    def __init__(self, choices=None, byte_count=None, read_skip_byte_count=0, write_prefix_bytes=b''):
        assert choices is not None
        assert isinstance(choices, _NamedInts)
        assert len(choices) > 1
        self.choices = choices
        self.needs_current_value = False

        max_bits = max(x.bit_length() for x in choices)
        self._byte_count = (max_bits // 8) + (1 if max_bits % 8 else 0)
        if byte_count:
            assert self._byte_count <= byte_count
            self._byte_count = byte_count
        assert self._byte_count < 8
        self._read_skip_byte_count = read_skip_byte_count
        self._write_prefix_bytes = write_prefix_bytes if write_prefix_bytes else b''
        assert self._byte_count + self._read_skip_byte_count <= 14
        assert self._byte_count + len(self._write_prefix_bytes) <= 14

    def to_string(self, value):
        return str(self.choices[value]) if isinstance(value, int) else str(value)

    def validate_read(self, reply_bytes):
        reply_value = _bytes2int(reply_bytes[self._read_skip_byte_count:self._read_skip_byte_count + self._byte_count])
        valid_value = self.choices[reply_value]
        assert valid_value is not None, '%s: failed to validate read value %02X' % (self.__class__.__name__, reply_value)
        return valid_value

    def prepare_write(self, new_value, current_value=None):
        if new_value is None:
            value = self.choices[:][0]
        else:
            value = self.choice(new_value)
        if value is None:
            raise ValueError('invalid choice %r' % new_value)
        assert isinstance(value, _NamedInt)
        return self._write_prefix_bytes + value.bytes(self._byte_count)

    def choice(self, value):
        if isinstance(value, int):
            return self.choices[value]
        try:
            int(value)
            if int(value) in self.choices:
                return self.choices[int(value)]
        except Exception:
            pass
        if value in self.choices:
            return self.choices[value]
        else:
            return None

    def acceptable(self, args, current):
        choice = self.choice(args[0]) if len(args) == 1 else None
        return None if choice is None else [choice]


class ChoicesMapValidator(ChoicesValidator):
    kind = KIND.map_choice
    keys_universe = None  # the possible keys, or an empty sequence for anything
    choices_universe = None  # the possible choices, or an empty sequence for anything

    def __init__(
        self,
        choices_map,
        key_byte_count=0,
        key_postfix_bytes=b'',
        byte_count=0,
        read_skip_byte_count=0,
        write_prefix_bytes=b'',
        extra_default=None,
        mask=-1,
        activate=0
    ):
        assert choices_map is not None
        assert isinstance(choices_map, dict)
        max_key_bits = 0
        max_value_bits = 0
        for key, choices in choices_map.items():
            assert isinstance(key, _NamedInt)
            assert isinstance(choices, _NamedInts)
            max_key_bits = max(max_key_bits, key.bit_length())
            for key_value in choices:
                assert isinstance(key_value, _NamedInt)
                max_value_bits = max(max_value_bits, key_value.bit_length())
        self._key_byte_count = (max_key_bits + 7) // 8
        if key_byte_count:
            assert self._key_byte_count <= key_byte_count
            self._key_byte_count = key_byte_count
        self._byte_count = (max_value_bits + 7) // 8
        if byte_count:
            assert self._byte_count <= byte_count
            self._byte_count = byte_count

        self.choices = choices_map
        self.needs_current_value = False
        self.extra_default = extra_default
        self._key_postfix_bytes = key_postfix_bytes
        self._read_skip_byte_count = read_skip_byte_count if read_skip_byte_count else 0
        self._write_prefix_bytes = write_prefix_bytes if write_prefix_bytes else b''
        self.activate = activate
        self.mask = mask
        assert self._byte_count + self._read_skip_byte_count + self._key_byte_count <= 14
        assert self._byte_count + len(self._write_prefix_bytes) + self._key_byte_count <= 14

    def to_string(self, value):
        def element_to_string(key, val):
            k, c = next(((k, c) for k, c in self.choices.items() if int(key) == k), (None, None))
            return str(k) + ':' + str(c[val]) if k is not None else '?'

        return '{' + ', '.join([element_to_string(k, value[k]) for k in sorted(value)]) + '}'

    def validate_read(self, reply_bytes, key):
        start = self._key_byte_count + self._read_skip_byte_count
        end = start + self._byte_count
        reply_value = _bytes2int(reply_bytes[start:end]) & self.mask
        # reprogrammable keys starts out as 0, which is not a choice, so don't use assert here
        if self.extra_default is not None and self.extra_default == reply_value:
            return int(self.choices[key][0])
        if reply_value not in self.choices[key]:
            assert reply_value in self.choices[
                key], '%s: failed to validate read value %02X' % (self.__class__.__name__, reply_value)
        return reply_value

    def prepare_key(self, key):
        return key.to_bytes(self._key_byte_count, 'big') + self._key_postfix_bytes

    def prepare_write(self, key, new_value):
        choices = self.choices.get(key)
        if choices is None or (new_value not in choices and new_value != self.extra_default):
            _log.error('invalid choice %r for %s', new_value, key)
            return None
        new_value = new_value | self.activate
        return self._write_prefix_bytes + new_value.to_bytes(self._byte_count, 'big')

    def acceptable(self, args, current):
        if len(args) != 2:
            return None
        key, choices = next(((key, item) for key, item in self.choices.items() if key == args[0]), (None, None))
        if choices is None or args[1] not in choices:
            return None
        choice = next((item for item in choices if item == args[1]), None)
        return [str(int(key)), int(choice)] if choice is not None else None

    def compare(self, args, current):
        if len(args) != 2:
            return False
        key = next((key for key in self.choices if key == int(args[0])), None)
        if key is None:
            return False
        return args[1] == current[str(int(key))]


class RangeValidator(Validator):
    kind = KIND.range
    """Translates between integers and a byte sequence.
    :param min_value: minimum accepted value (inclusive)
    :param max_value: maximum accepted value (inclusive)
    :param byte_count: the size of the derived byte sequence. If None, it
    will be calculated from the range."""
    min_value = 0
    max_value = 255

    @classmethod
    def build(cls, setting_class, device, **kwargs):
        kwargs['min_value'] = setting_class.min_value
        kwargs['max_value'] = setting_class.max_value
        return cls(**kwargs)

    def __init__(self, min_value=0, max_value=255, byte_count=1):
        assert max_value > min_value
        self.min_value = min_value
        self.max_value = max_value
        self.needs_current_value = False

        self._byte_count = math.ceil(math.log(max_value + 1, 256))
        if byte_count:
            assert self._byte_count <= byte_count
            self._byte_count = byte_count
        assert self._byte_count < 8

    def validate_read(self, reply_bytes):
        reply_value = _bytes2int(reply_bytes[:self._byte_count])
        assert reply_value >= self.min_value, '%s: failed to validate read value %02X' % (self.__class__.__name__, reply_value)
        assert reply_value <= self.max_value, '%s: failed to validate read value %02X' % (self.__class__.__name__, reply_value)
        return reply_value

    def prepare_write(self, new_value, current_value=None):
        if new_value < self.min_value or new_value > self.max_value:
            raise ValueError('invalid choice %r' % new_value)
        return _int2bytes(new_value, self._byte_count)

    def acceptable(self, args, current):
        arg = args[0]
        #  None if len(args) != 1 or type(arg) != int or arg < self.min_value or arg > self.max_value else args)
        return None if len(args) != 1 or type(arg) != int or arg < self.min_value or arg > self.max_value else args

    def compare(self, args, current):
        if len(args) == 1:
            return args[0] == current
        elif len(args) == 2:
            return args[0] <= current and current <= args[1]
        else:
            return False


class MultipleRangeValidator(Validator):

    kind = KIND.multiple_range

    def __init__(self, items, sub_items):
        assert isinstance(items, list)  # each element must have .index and its __int__ must return its id (not its index)
        assert isinstance(sub_items, dict)
        # sub_items: items -> class with .minimum, .maximum, .length (in bytes), .id (a string) and .widget (e.g. 'Scale')
        self.items = items
        self.keys = _NamedInts(**{str(item): int(item) for item in items})
        self._item_from_id = {int(k): k for k in items}
        self.sub_items = sub_items

    def prepare_read_item(self, item):
        return _int2bytes((self._item_from_id[int(item)].index << 1) | 0xFF, 2)

    def validate_read_item(self, reply_bytes, item):
        item = self._item_from_id[int(item)]
        start = 0
        value = {}
        for sub_item in self.sub_items[item]:
            r = reply_bytes[start:start + sub_item.length]
            if len(r) < sub_item.length:
                r += b'\x00' * (sub_item.length - len(value))
            v = _bytes2int(r)
            if not (sub_item.minimum < v < sub_item.maximum):
                _log.warn(
                    f'{self.__class__.__name__}: failed to validate read value for {item}.{sub_item}: ' +
                    f'{v} not in [{sub_item.minimum}..{sub_item.maximum}]'
                )
            value[str(sub_item)] = v
            start += sub_item.length
        return value

    def prepare_write(self, value):
        seq = []
        w = b''
        for item in value.keys():
            _item = self._item_from_id[int(item)]
            b = _int2bytes(_item.index, 1)
            for sub_item in self.sub_items[_item]:
                try:
                    v = value[str(int(item))][str(sub_item)]
                except KeyError:
                    return None
                if not (sub_item.minimum <= v <= sub_item.maximum):
                    raise ValueError(
                        f'invalid choice for {item}.{sub_item}: {v} not in [{sub_item.minimum}..{sub_item.maximum}]'
                    )
                b += _int2bytes(v, sub_item.length)
            if len(w) + len(b) > 15:
                seq.append(b + b'\xFF')
                w = b''
            w += b
        seq.append(w + b'\xFF')
        return seq

    def prepare_write_item(self, item, value):
        _item = self._item_from_id[int(item)]
        w = _int2bytes(_item.index, 1)
        for sub_item in self.sub_items[_item]:
            try:
                v = value[str(sub_item)]
            except KeyError:
                return None
            if not (sub_item.minimum <= v <= sub_item.maximum):
                raise ValueError(f'invalid choice for {item}.{sub_item}: {v} not in [{sub_item.minimum}..{sub_item.maximum}]')
            w += _int2bytes(v, sub_item.length)
        return w + b'\xFF'

    def acceptable(self, args, current):
        # just one item, with at least one sub-item
        if not isinstance(args, list) or len(args) != 2 or not isinstance(args[1], dict):
            return None
        item = next((p for p in self.items if p.id == args[0] or str(p) == args[0]), None)
        if not item:
            return None
        for sub_key, value in args[1].items():
            sub_item = next((it for it in self.sub_items[item] if it.id == sub_key), None)
            if not sub_item:
                return None
            if not isinstance(value, int) or not (sub_item.minimum <= value <= sub_item.maximum):
                return None
        return [str(int(item)), {**args[1]}]

    def commpare(self, args, current):
        _log.warn('compare not implemented for multiple range settings')
        return False


class ActionSettingRW:
    """Special RW class for settings that turn on and off special processing when a key or button is depressed"""
    def __init__(self, feature, name='', divert_setting_name='divert-keys'):
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
        return _int2bytes(self.key.key, 2) if self.active and self.key else b'\x00\x00'

    def write(self, device, data_bytes):
        def handler(device, n):  # Called on notification events from the device
            if n.sub_id < 0x40 and device.features[n.sub_id] == _hidpp20.FEATURE.REPROG_CONTROLS_V4:
                if n.address == 0x00:
                    cids = _unpack('!HHHH', n.data[:8])
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
                        dx, dy = _unpack('!hh', n.data[:4])
                        self.move_action(dx, dy)

        divertSetting = next(filter(lambda s: s.name == self.divert_setting_name, device.settings), None)
        if divertSetting is None:
            _log.warn('setting %s not found on %s', self.divert_setting_name, device.name)
            return None
        self.device = device
        key = _bytes2int(data_bytes)
        if key:  # Enable
            self.key = next((k for k in device.keys if k.key == key), None)
            if self.key:
                self.active = True
                if divertSetting:
                    divertSetting.write_key_value(int(self.key.key), 1)
                device.add_notification_handler(self.name, handler)
                from solaar.ui import status_changed as _status_changed
                self.activate_action()
                _status_changed(device, refresh=True)  # update main window
            else:
                _log.error('cannot enable %s on %s for key %s', self.name, device, key)
        else:  # Disable
            if self.active:
                self.active = False
                if divertSetting:
                    divertSetting.write_key_value(int(self.key.key), 0)
                from solaar.ui import status_changed as _status_changed
                _status_changed(device, refresh=True)  # update main window
                try:
                    device.remove_notification_handler(self.name)
                except Exception:
                    if _log.isEnabledFor(_WARNING):
                        _log.warn('cannot disable %s on %s', self.name, device)
                self.deactivate_action()
        return True


def apply_all_settings(device):
    persister = getattr(device, 'persister', None)
    sensitives = persister.get('_sensitive', {}) if persister else {}
    for s in device.settings:
        ignore = sensitives.get(s.name, False)
        if ignore != SENSITIVITY_IGNORE:
            s.apply()
