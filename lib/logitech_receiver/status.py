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

import logging

from . import hidpp10
from . import hidpp10_constants as _hidpp10_constants
from . import hidpp20_constants as _hidpp20_constants
from . import settings as _settings
from .common import Battery, NamedInts
from .i18n import _, ngettext

logger = logging.getLogger(__name__)

_R = _hidpp10_constants.REGISTERS

_hidpp10 = hidpp10.Hidpp10()

ALERT = NamedInts(NONE=0x00, NOTIFICATION=0x01, SHOW_WINDOW=0x02, ATTENTION=0x04, ALL=0xFF)

KEYS = NamedInts(LINK_ENCRYPTED=5, NOTIFICATION_FLAGS=6, ERROR=7)


def attach_to(device, changed_callback):
    assert device
    assert changed_callback

    if not hasattr(device, "status") or device.status is None:
        if not device.isDevice:
            device.status = ReceiverStatus(device, changed_callback)
        else:
            device.status = DeviceStatus(device, changed_callback)


class ReceiverStatus(dict):
    """The 'runtime' status of a receiver, mostly about the pairing process --
    is the pairing lock open or closed, any pairing errors, etc.
    """

    def __init__(self, receiver, changed_callback):
        assert receiver
        self._receiver = receiver

        assert changed_callback
        self._changed_callback = changed_callback

        self.lock_open = False
        self.discovering = False
        self.counter = None
        self.device_address = None
        self.device_authentication = None
        self.device_kind = None
        self.device_name = None
        self.device_passkey = None
        self.new_device = None

        self[KEYS.ERROR] = None

    def to_string(self):
        count = len(self._receiver)
        return (
            _("No paired devices.")
            if count == 0
            else ngettext("%(count)s paired device.", "%(count)s paired devices.", count) % {"count": count}
        )

    def __str__(self):
        self.to_string()

    def changed(self, alert=ALERT.NOTIFICATION, reason=None):
        self._changed_callback(self._receiver, alert=alert, reason=reason)


class DeviceStatus(dict):
    """Holds the 'runtime' status of a peripheral
    Currently _active, battery -- dict entries are being moved to attributs
    Updates mostly come from incoming notification events from the device itself.
    """

    def __init__(self, device, changed_callback):
        assert device
        self._device = device
        assert changed_callback
        self._changed_callback = changed_callback
        self._active = None  # is the device active?
        self.battery = None

    def to_string(self):
        return self.battery.to_str() if self.battery is not None else ""

    def __repr__(self):
        return "{" + ", ".join("'%s': %r" % (k, v) for k, v in self.items()) + "}"

    def __bool__(self):
        return bool(self._active)

    __nonzero__ = __bool__

    def set_battery_info(self, info):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: battery %s, %s", self._device, info.level, info.status)
        if info.level is None and self.battery:  # use previous level if missing from new information
            info.level = self.battery.level

        changed = self.battery != info
        self.battery = info

        alert, reason = ALERT.NONE, None
        if info.ok():
            self[KEYS.ERROR] = None
        else:
            logger.warning("%s: battery %d%%, ALERT %s", self._device, info.level, info.status)
            if self.get(KEYS.ERROR) != info.status:
                self[KEYS.ERROR] = info.status
                alert = ALERT.NOTIFICATION | ALERT.ATTENTION
            reason = info.to_str()

        if changed or reason or not self._active:  # a battery response means device is active
            # update the leds on the device, if any
            _hidpp10.set_3leds(self._device, info.level, charging=info.charging(), warning=bool(alert))
            self.changed(active=True, alert=alert, reason=reason)

    # Retrieve and regularize battery status
    def read_battery(self):
        if self._active:
            battery = self._device.battery()
            self.set_battery_info(battery if battery is not None else Battery(None, None, None, None))

    def changed(self, active=None, alert=ALERT.NONE, reason=None, push=False):
        d = self._device

        if active is not None:
            d.online = active
            was_active, self._active = self._active, active
            if active:
                if not was_active:
                    # Make sure to set notification flags on the device, they
                    # get cleared when the device is turned off (but not when the device
                    # goes idle, and we can't tell the difference right now).
                    if d.protocol < 2.0:
                        self[KEYS.NOTIFICATION_FLAGS] = d.enable_connection_notifications()
                    # battery information may have changed so try to read it now
                    self.read_battery()

                # Push settings for new devices when devices request software reconfiguration
                # and when devices become active if they don't have wireless device status feature,
                if (
                    was_active is None
                    or push
                    or not was_active
                    and (not d.features or _hidpp20_constants.FEATURE.WIRELESS_DEVICE_STATUS not in d.features)
                ):
                    if logger.isEnabledFor(logging.INFO):
                        logger.info("%s pushing device settings %s", d, d.settings)
                    _settings.apply_all_settings(d)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("device %d changed: active=%s %s", d.number, self._active, self.battery)
        self._changed_callback(d, alert, reason)
