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

from logging import DEBUG as _DEBUG
from logging import INFO as _INFO
from logging import getLogger
from time import time as _timestamp

from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20
from . import settings as _settings
from .common import BATTERY_APPROX as _BATTERY_APPROX
from .common import NamedInt as _NamedInt
from .common import NamedInts as _NamedInts
from .i18n import _, ngettext

_log = getLogger(__name__)
del getLogger

_R = _hidpp10.REGISTERS

#
#
#

ALERT = _NamedInts(NONE=0x00, NOTIFICATION=0x01, SHOW_WINDOW=0x02, ATTENTION=0x04, ALL=0xFF)

KEYS = _NamedInts(
    BATTERY_LEVEL=1,
    BATTERY_CHARGING=2,
    BATTERY_STATUS=3,
    LIGHT_LEVEL=4,
    LINK_ENCRYPTED=5,
    NOTIFICATION_FLAGS=6,
    ERROR=7,
    BATTERY_NEXT_LEVEL=8,
    BATTERY_VOLTAGE=9,
)

# If the battery charge is under this percentage, trigger an attention event
# (blink systray icon/notification/whatever).
_BATTERY_ATTENTION_LEVEL = 5

# If no updates have been receiver from the device for a while, ping the device
# and update it status accordingly.
# _STATUS_TIMEOUT = 5 * 60  # seconds
_LONG_SLEEP = 15 * 60  # seconds

#
#
#


def attach_to(device, changed_callback):
    assert device
    assert changed_callback

    if not hasattr(device, 'status') or device.status is None:
        if not device.isDevice:
            device.status = ReceiverStatus(device, changed_callback)
        else:
            device.status = DeviceStatus(device, changed_callback)


#
#
#


class ReceiverStatus(dict):
    """The 'runtime' status of a receiver, mostly about the pairing process --
    is the pairing lock open or closed, any pairing errors, etc.
    """
    def __init__(self, receiver, changed_callback):
        assert receiver
        self._receiver = receiver

        assert changed_callback
        self._changed_callback = changed_callback

        # self.updated = 0

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

    def __str__(self):
        count = len(self._receiver)
        return (
            _('No paired devices.')
            if count == 0 else ngettext('%(count)s paired device.', '%(count)s paired devices.', count) % {
                'count': count
            }
        )

    def changed(self, alert=ALERT.NOTIFICATION, reason=None):
        # self.updated = _timestamp()
        self._changed_callback(self._receiver, alert=alert, reason=reason)

    # def poll(self, timestamp):
    #     r = self._receiver
    #     assert r
    #
    #     if _log.isEnabledFor(_DEBUG):
    #         _log.debug("polling status of %s", r)
    #
    #     # make sure to read some stuff that may be read later by the UI
    #     r.serial, r.firmware, None
    #
    #     # get an update of the notification flags
    #     # self[KEYS.NOTIFICATION_FLAGS] = _hidpp10.get_notification_flags(r)


#
#
#


class DeviceStatus(dict):
    """Holds the 'runtime' status of a peripheral -- things like
    active/inactive, battery charge, lux, etc. It updates them mostly by
    processing incoming notification events from the device itself.
    """
    def __init__(self, device, changed_callback):
        assert device
        self._device = device

        assert changed_callback
        self._changed_callback = changed_callback

        # is the device active?
        self._active = None

        # timestamp of when this status object was last updated
        self.updated = 0

    def to_string(self):
        def _items():
            comma = False

            battery_level = self.get(KEYS.BATTERY_LEVEL)
            if battery_level is not None:
                if isinstance(battery_level, _NamedInt):
                    yield _('Battery: %(level)s') % {'level': _(str(battery_level))}
                else:
                    yield _('Battery: %(percent)d%%') % {'percent': battery_level}

                battery_status = self.get(KEYS.BATTERY_STATUS)
                if battery_status is not None:
                    yield ' (%s)' % _(str(battery_status))

                comma = True

            light_level = self.get(KEYS.LIGHT_LEVEL)
            if light_level is not None:
                if comma:
                    yield ', '
                yield _('Lighting: %(level)s lux') % {'level': light_level}

        return ''.join(i for i in _items())

    def __repr__(self):
        return '{' + ', '.join('\'%s\': %r' % (k, v) for k, v in self.items()) + '}'

    def __bool__(self):
        return bool(self._active)

    __nonzero__ = __bool__

    def set_battery_info(self, level, nextLevel, status, voltage, timestamp=None):
        if _log.isEnabledFor(_DEBUG):
            _log.debug('%s: battery %s, %s', self._device, level, status)

        if level is None:
            # Some notifications may come with no battery level info, just
            # charging state info, so do our best to infer a level (even if it is just the last level)
            # It is not always possible to do this well
            if status == _hidpp20.BATTERY_STATUS.full:
                level = _BATTERY_APPROX.full
            elif status in (_hidpp20.BATTERY_STATUS.almost_full, _hidpp20.BATTERY_STATUS.recharging):
                level = _BATTERY_APPROX.good
            elif status == _hidpp20.BATTERY_STATUS.slow_recharge:
                level = _BATTERY_APPROX.low
            else:
                level = self.get(KEYS.BATTERY_LEVEL)
        else:
            assert isinstance(level, int)

        # TODO: this is also executed when pressing Fn+F7 on K800.
        old_level, self[KEYS.BATTERY_LEVEL] = self.get(KEYS.BATTERY_LEVEL), level
        old_status, self[KEYS.BATTERY_STATUS] = self.get(KEYS.BATTERY_STATUS), status
        self[KEYS.BATTERY_NEXT_LEVEL] = nextLevel
        old_voltage, self[KEYS.BATTERY_VOLTAGE] = self.get(KEYS.BATTERY_VOLTAGE), voltage

        charging = status in (
            _hidpp20.BATTERY_STATUS.recharging, _hidpp20.BATTERY_STATUS.almost_full, _hidpp20.BATTERY_STATUS.full,
            _hidpp20.BATTERY_STATUS.slow_recharge
        )
        old_charging, self[KEYS.BATTERY_CHARGING] = self.get(KEYS.BATTERY_CHARGING), charging

        changed = old_level != level or old_status != status or old_charging != charging or old_voltage != voltage
        alert, reason = ALERT.NONE, None

        if _hidpp20.BATTERY_OK(status) and (level is None or level > _BATTERY_ATTENTION_LEVEL):
            self[KEYS.ERROR] = None
        else:
            _log.warn('%s: battery %d%%, ALERT %s', self._device, level, status)
            if self.get(KEYS.ERROR) != status:
                self[KEYS.ERROR] = status
                # only show the notification once
                alert = ALERT.NOTIFICATION | ALERT.ATTENTION
            if isinstance(level, _NamedInt):
                reason = _('Battery: %(level)s (%(status)s)') % {'level': _(level), 'status': _(status)}
            else:
                reason = _('Battery: %(percent)d%% (%(status)s)') % {'percent': level, 'status': status.name}

        if changed or reason or not self._active:  # a battery response means device is active
            # update the leds on the device, if any
            _hidpp10.set_3leds(self._device, level, charging=charging, warning=bool(alert))
            self.changed(active=True, alert=alert, reason=reason, timestamp=timestamp)

    # Retrieve and regularize battery status
    def read_battery(self, timestamp=None):
        if self._active:
            assert self._device
            battery = self._device.battery()
            self.set_battery_keys(battery)

    def set_battery_keys(self, battery):
        if battery is not None:
            level, nextLevel, status, voltage = battery
            self.set_battery_info(level, nextLevel, status, voltage)
        elif self.get(KEYS.BATTERY_STATUS, None) is not None:
            self[KEYS.BATTERY_STATUS] = None
            self[KEYS.BATTERY_CHARGING] = None
            self[KEYS.BATTERY_VOLTAGE] = None
            self.changed()

    def changed(self, active=None, alert=ALERT.NONE, reason=None, push=False, timestamp=None):
        assert self._changed_callback
        d = self._device
        # assert d  # may be invalid when processing the 'unpaired' notification
        timestamp = timestamp or _timestamp()

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
                    self.read_battery(timestamp)

                # Push settings for new devices (was_active is None),
                # when devices request software reconfiguration
                # and when devices become active if they don't have wireless device status feature,
                if was_active is None or push or not was_active and (
                    not d.features or _hidpp20.FEATURE.WIRELESS_DEVICE_STATUS not in d.features
                ):
                    if _log.isEnabledFor(_INFO):
                        _log.info('%s pushing device settings %s', d, d.settings)
                    _settings.apply_all_settings(d)

            else:
                if was_active:
                    battery = self.get(KEYS.BATTERY_LEVEL)
                    self.clear()
                    # If we had a known battery level before, assume it's not going
                    # to change much while the device is offline.
                    if battery is not None:
                        self[KEYS.BATTERY_LEVEL] = battery

        # A device that is not active on the first status notification
        # but becomes active afterwards does not produce a pop-up notification
        # so don't produce one here.  This cuts off pop-ups when Solaar starts,
        # which can be problematic if Solaar is autostarted.
        ## if self.updated == 0 and active is True:
        ## if the device is active on the very first status notification,
        ## (meaning just when the program started or a new receiver was just
        ## detected), pop up a notification about it
        ##    alert |= ALERT.NOTIFICATION

        self.updated = timestamp

        # if _log.isEnabledFor(_DEBUG):
        #     _log.debug("device %d changed: active=%s %s", d.number, self._active, dict(self))
        self._changed_callback(d, alert, reason)

    # def poll(self, timestamp):
    #     d = self._device
    #     if not d:
    #         _log.error("polling status of invalid device")
    #         return
    #
    #     if self._active:
    #         if _log.isEnabledFor(_DEBUG):
    #             _log.debug("polling status of %s", d)
    #
    #         # read these from the device, the UI may need them later
    #         d.protocol, d.serial, d.firmware, d.kind, d.name, d.settings, None
    #
    #         # make sure we know all the features of the device
    #         # if d.features:
    #         #     d.features[:]
    #
    #         # devices may go out-of-range while still active, or the computer
    #         # may go to sleep and wake up without the devices available
    #         if timestamp - self.updated > _STATUS_TIMEOUT:
    #             if d.ping():
    #                 timestamp = self.updated = _timestamp()
    #             else:
    #                 self.changed(active=False, reason='out of range')
    #
    #         # if still active, make sure we know the battery level
    #         if KEYS.BATTERY_LEVEL not in self:
    #             self.read_battery(timestamp)
    #
    #     elif timestamp - self.updated > _STATUS_TIMEOUT:
    #         if d.ping():
    #             self.changed(active=True)
    #         else:
    #             self.updated = _timestamp()
