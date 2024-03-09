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
from .common import NamedInts

logger = logging.getLogger(__name__)

_R = _hidpp10_constants.REGISTERS

_hidpp10 = hidpp10.Hidpp10()

ALERT = NamedInts(NONE=0x00, NOTIFICATION=0x01, SHOW_WINDOW=0x02, ATTENTION=0x04, ALL=0xFF)


def attach_to(device, changed_callback):
    assert device
    assert changed_callback

    if not hasattr(device, "status") or device.status is None:
        if not device.isDevice:
            device.status = ReceiverStatus(device, changed_callback)
        else:
            device.status = DeviceStatus(device, changed_callback)


class ReceiverStatus:
    """The 'runtime' status of a receiver, currently vestigial."""

    def __init__(self, receiver, changed_callback):
        assert receiver
        self._receiver = receiver
        assert changed_callback
        self._changed_callback = changed_callback

    def changed(self, alert=ALERT.NOTIFICATION, reason=None):
        self._changed_callback(self._receiver, alert=alert, reason=reason)


class DeviceStatus:
    """Holds the 'runtime' status of a peripheral
    Currently _active, battery, link_encrypted, notification_flags, error
    Updates mostly come from incoming notification events from the device itself.
    """

    def __init__(self, device, changed_callback):
        assert device
        self._device = device
        assert changed_callback
        self._changed_callback = changed_callback
        self._active = None  # is the device active?
        self.link_encrypted = None

    def __bool__(self):
        return bool(self._active)

    __nonzero__ = __bool__

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
                        self._device.notification_flags = d.enable_connection_notifications()
                    # battery information may have changed so try to read it now
                    self._device.read_battery()

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
