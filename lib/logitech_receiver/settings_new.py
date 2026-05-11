## Copyright (C) 2025  Solaar contributors
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

## A new way of supporting settings, using a feature-specifi device class to store, read, and write relevant information
## The setting uses the device class to interact with the device feature.
## The setting uses a persist class to keep track of the setting.

## Interface:

import logging

from .settings import Kind

logger = logging.getLogger(__name__)


class Setting:
    name = None  # Solaar internal name for the setting
    label = None  # Solaar user name for the setting (translatable)
    description = None  # Solaar extra desciption for the setting (translatable)
    feature = None  # Logitech feature that the setting uses
    min_version = 0  # Minimum version of the feature needed
    setup = None  # method name on Device class to get the device object
    get = None  # method name on the device object to get the setting value
    set = None  # method name on the device object to set the setting value
    acceptable = None  # method name on the device object to check for acceptable values
    choices_universe = None  # All possible acceptable keys, for settings with keys
    kind = Kind.NONE  # What GUI interface to use
    persist = True  # Whether to remember the setting
    display = True  # display setting in UI
    _device = None  # The device that this setting is for
    _device_object = None  # The object that interacts with the feature for the device
    _value = None  # Stored value as maintained by Solaar, used for persistence

    def __init__(self, device, device_object):
        self._device = device
        self._device_object = device_object

    @classmethod
    def build(cls, device):
        cls.check_properties(cls)
        device_object = getattr(device, cls.setup)()
        if device_object:
            setting = cls(device, device_object)
            return setting

    @classmethod
    def check_properties(cl, cls):
        assert cls.name and cls.label and cls.description, "New settings require a name, label, and description"
        assert cls.feature, "New settings require a feature"
        assert cls.setup, "New settings require a setup device method"
        assert cls.get and cls.set and cls.acceptable, "New settings require get, set, and acceptable methods"

    def setup_from_class(self, clss):
        """Copy settings methods for a new setting from a settting class"""
        self.name = clss.name
        self.label = clss.label
        self.description = clss.description
        self.feature = clss.feature
        self.min_version = clss.min_version
        self.setup = clss.setup
        self.get = clss.get
        self.set = clss.set
        self.acceptable = clss.acceptable
        self.choices_universe = clss.choices_universe
        self.kind = clss.kind
        self.persist = clss.persist

    def _pre_read(self, cached):
        """Get information from and save information to the persister"""
        # Get the persister map if available and not done already
        if self.persist and self._value is None and getattr(self._device, "persister", None):
            self._value = self._device.persister.get(self.name)
        # If this is new save its current value for the next time
        if cached and self._value is not None:
            if getattr(self._device, "persister", None) and self.name not in self._device.persister:
                self._device.persister[self.name] = self._value if self.persist else None

    def read(self, cached=True):
        """Get all the data for the setting.  If cached is True the data in the _value can be used."""
        self._pre_read(cached)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: setting read %r from %s", self.name, self._value, self._device)
        if cached and self._value is not None:
            return self._value
        if cached:
            self._value = getattr(self._device_object, self.get)()
            return self._value
        if self._device.online:
            self._value = getattr(self._device_object.query(), self.get)()
            return self._value

    def write(self, value, save=True):
        """Write the value to the device.  If saved is True also save in the persister"""
        pass  ## fill out

    def apply(self):
        """Write saved data to the device, using persisted data if available"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: apply (%s)", self.name, self._device)
        value = None
        try:
            value = self.read(self.persist)  # Don't use persisted value if setting doesn't persist
            if self.persist and value is not None:  # If setting doesn't persist no need to write value just read
                self.write(value, save=False)
        except Exception as e:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("%s: error applying %s so ignore it (%s): %s", self.name, value, self._device, repr(e))

    @property
    def range(self):
        if self.kind == Kind.RANGE:
            return self.min_value, self.max_value

    def val_to_string(self, value):
        return str(value)


## key mapping from symbols to values????


class Settings(Setting):
    """A setting descriptor for multiple keys.
    Supported by a class that provides the interface to the device, see ForceSensingButtonArray in hidpp20.py
    Picks out a field from the mapped device feature objects."""

    # setup creates a dictionary with entries for all the keys
    # _value is a map from keys to values
    # get, set, and acceptable are methods of dict value objects, not of the device object itself  #### FIX THIS! MAYBE??

    def __init__(self, device, device_object):
        super().__init__(device, device_object)
        self._value = {}

    def read(self, cached=True):
        self._pre_read(cached)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: settings read %r from %s", self.name, self._value, self._device)
        for key in self._device_object:
            self.read_key(key, cached)
        return self._value

    def read_key(self, key, cached=True):
        """Get the data for the key.  If cached is True the data in the device_object can be used."""
        self._pre_read(cached)
        if key not in self._device_object:
            logger.error("%s: settings illegal read key %r for %s", self.name, key, self._device)
            return None
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: settings key %r read %r from %s", self.name, key, self._value, self._device)
        if cached and key in self._value and self._value[key] is not None:
            return self._value[key]
        if cached:
            data = self._device_object[key]
            self._value[key] = getattr(data, self.get)()
            return self._value[key]
        if self._device.online:
            data = self._device_object.query_key(key)
            self._value[key] = getattr(data, self.get)()
            return self._value[key]

    def write(self, value, save=True):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: settings read %r from %s", self.name, self._value, self._device)
        if isinstance(value, dict):
            for key, val in value.items():
                self.write_key_value(key, val, save)
        else:  # to mimic interface for non-dict setting
            key = next(iter(self._device_object))
            self.write_key_value(key, value, save)
        return value

    def write_key_value(self, key, value, save=True):
        """Write the data for the key.  If saved is True also save in the persister"""
        if key not in self._device_object:
            logger.error("%s: settings illegal write key %r for %s", self.name, key, self._device)
            return None
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: settings write key %r value %r to %s", self.name, key, value, self._device)
        if self._device.online:
            if self._device_object[key] is None:
                self.read_key(key)
            if self._device_object[key] is None:
                logger.error("%s: settings illegal write key %r for %s", self.name, key, self._device)
                return None
            if not getattr(self._device_object[key], self.acceptable)(value):
                logger.error("%s: settings illegal write key %r value %r for %s", self.name, key, value, self._device)
                return None
            self._value[key] = value
            if self._device.persister and self.persist and save:
                self._device.persister[self.name][key] = value
            getattr(self._device_object[key], self.set)(value)
            return value
