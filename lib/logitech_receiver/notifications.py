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

# Handles incoming events from the receiver/devices, updating the related
# status object as appropriate.

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import DEBUG as _DEBUG
from logging import INFO as _INFO
from logging import WARNING as _WARNING
from logging import getLogger

from . import diversion as _diversion
from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20
from .base import DJ_MESSAGE_ID as _DJ_MESSAGE_ID
from .common import strhex as _strhex
from .common import unpack as _unpack
from .i18n import _
from .status import ALERT as _ALERT
from .status import KEYS as _K

_log = getLogger(__name__)
del getLogger

_R = _hidpp10.REGISTERS
_F = _hidpp20.FEATURE

#
#
#


def process(device, notification):
    assert device
    assert notification

    assert hasattr(device, 'status')
    status = device.status
    assert status is not None

    if device.kind is None:
        return _process_receiver_notification(device, status, notification)

    return _process_device_notification(device, status, notification)


#
#
#


def _process_receiver_notification(receiver, status, n):
    # supposedly only 0x4x notifications arrive for the receiver
    assert n.sub_id & 0x40 == 0x40

    # pairing lock notification
    if n.sub_id == 0x4A:
        status.lock_open = bool(n.address & 0x01)
        reason = (_('pairing lock is open') if status.lock_open else _('pairing lock is closed'))
        if _log.isEnabledFor(_INFO):
            _log.info('%s: %s', receiver, reason)

        status[_K.ERROR] = None
        if status.lock_open:
            status.new_device = None

        pair_error = ord(n.data[:1])
        if pair_error:
            status[_K.ERROR] = error_string = _hidpp10.PAIRING_ERRORS[pair_error]
            status.new_device = None
            _log.warn('pairing error %d: %s', pair_error, error_string)

        status.changed(reason=reason)
        return True

    _log.warn('%s: unhandled notification %s', receiver, n)


#
#
#


def _process_device_notification(device, status, n):
    # incoming packets with SubId >= 0x80 are supposedly replies from
    # HID++ 1.0 requests, should never get here
    assert n.sub_id & 0x80 == 0

    # Allow the device object to handle the notification using custom
    # per-device state.
    handling_ret = device.handle_notification(n)
    if handling_ret is not None:
        return handling_ret

    # 0x40 to 0x7F appear to be HID++ 1.0 or DJ notifications
    if n.sub_id >= 0x40:
        if n.report_id == _DJ_MESSAGE_ID:
            return _process_dj_notification(device, status, n)
        else:
            return _process_hidpp10_notification(device, status, n)

    # At this point, we need to know the device's protocol, otherwise it's
    # possible to not know how to handle it.
    assert device.protocol is not None

    # some custom battery events for HID++ 1.0 devices
    if device.protocol < 2.0:
        return _process_hidpp10_custom_notification(device, status, n)

    # assuming 0x00 to 0x3F are feature (HID++ 2.0) notifications
    if not device.features:
        _log.warn('%s: feature notification but features not set up: %02X %s', device, n.sub_id, n)
        return False
    try:
        feature = device.features[n.sub_id]
    except IndexError:
        _log.warn('%s: notification from invalid feature index %02X: %s', device, n.sub_id, n)
        return False

    return _process_feature_notification(device, status, n, feature)


def _process_dj_notification(device, status, n):
    if _log.isEnabledFor(_DEBUG):
        _log.debug('%s (%s) DJ %s', device, device.protocol, n)

    if n.sub_id == 0x40:
        # do all DJ paired notifications also show up as HID++ 1.0 notifications?
        if _log.isEnabledFor(_INFO):
            _log.info('%s: ignoring DJ unpaired: %s', device, n)
        return True

    if n.sub_id == 0x41:
        # do all DJ paired notifications also show up as HID++ 1.0 notifications?
        if _log.isEnabledFor(_INFO):
            _log.info('%s: ignoring DJ paired: %s', device, n)
        return True

    if n.sub_id == 0x42:
        connected = not n.address & 0x01
        if _log.isEnabledFor(_INFO):
            _log.info('%s: DJ connection: %s %s', device, connected, n)
        status.changed(active=connected, alert=_ALERT.NONE, reason=_('connected') if connected else _('disconnected'))
        return True

    _log.warn('%s: unrecognized DJ %s', device, n)


def _process_hidpp10_custom_notification(device, status, n):
    if _log.isEnabledFor(_DEBUG):
        _log.debug('%s (%s) custom notification %s', device, device.protocol, n)

    if n.sub_id in (_R.battery_status, _R.battery_charge):
        # message layout: 10 ix <register> <xx> <yy> <zz> <00>
        assert n.data[-1:] == b'\x00'
        data = chr(n.address).encode() + n.data
        charge, status_text, next_charge = _hidpp10.parse_battery_status(n.sub_id, data)
        status.set_battery_info(charge, status_text, next_charge)
        return True

    if n.sub_id == _R.keyboard_illumination:
        # message layout: 10 ix 17("address")  <??> <?> <??> <light level 1=off..5=max>
        # TODO anything we can do with this?
        if _log.isEnabledFor(_INFO):
            _log.info('illumination event: %s', n)
        return True

    _log.warn('%s: unrecognized %s', device, n)


def _process_hidpp10_notification(device, status, n):
    # unpair notification
    if n.sub_id == 0x40:
        if n.address == 0x02:
            # device un-paired
            status.clear()
            device.wpid = None
            device.status = None
            if device.number in device.receiver:
                del device.receiver[device.number]
            status.changed(active=False, alert=_ALERT.ALL, reason=_('unpaired'))
        else:
            _log.warn('%s: disconnection with unknown type %02X: %s', device, n.address, n)
        return True

    # wireless link notification
    if n.sub_id == 0x41:
        protocol_name = (
            'Bluetooth' if n.address == 0x01 else '27 MHz' if n.address == 0x02 else
            'QUAD or eQUAD' if n.address == 0x03 else 'eQUAD step 4 DJ' if n.address == 0x04 else 'DFU Lite' if n.address ==
            0x05 else 'eQUAD step 4 Lite' if n.address == 0x06 else 'eQUAD step 4 Gaming' if n.address ==
            0x07 else 'eQUAD step 4 for gamepads' if n.address == 0x08 else 'eQUAD nano Lite' if n.address ==
            0x0A else 'Lightspeed 1' if n.address == 0x0C else 'Lightspeed 1_1' if n.address == 0x0D else None
        )
        if protocol_name:
            wpid = _strhex(n.data[2:3] + n.data[1:2])
            # workaround for short EX100 and other 27 MHz wpids
            if protocol_name == '27 MHz':
                wpid = '00' + _strhex(n.data[2:3])
            if wpid != device.wpid:
                _log.warn('%s wpid mismatch, got %s', device, wpid)
            flags = ord(n.data[:1]) & 0xF0
            link_encrypted = bool(flags & 0x20)
            link_established = not (flags & 0x40)
            if _log.isEnabledFor(_DEBUG):
                sw_present = bool(flags & 0x10)
                has_payload = bool(flags & 0x80)
                _log.debug(
                    '%s: %s connection notification: software=%s, encrypted=%s, link=%s, payload=%s', device, protocol_name,
                    sw_present, link_encrypted, link_established, has_payload
                )
            status[_K.LINK_ENCRYPTED] = link_encrypted
            status.changed(active=link_established)
        else:
            _log.warn('%s: connection notification with unknown protocol %02X: %s', device.number, n.address, n)

        return True

    if n.sub_id == 0x49:
        # raw input event? just ignore it
        # if n.address == 0x01, no idea what it is, but they keep on coming
        # if n.address == 0x03, appears to be an actual input event,
        #     because they only come when input happents
        return True

    # power notification
    if n.sub_id == 0x4B:
        if n.address == 0x01:
            if _log.isEnabledFor(_DEBUG):
                _log.debug('%s: device powered on', device)
            reason = status.to_string() or _('powered on')
            status.changed(active=True, alert=_ALERT.NOTIFICATION, reason=reason)
        else:
            _log.warn('%s: unknown %s', device, n)
        return True

    _log.warn('%s: unrecognized %s', device, n)


def _process_feature_notification(device, status, n, feature):
    if feature == _F.BATTERY_STATUS:
        if n.address == 0x00:
            discharge_level = ord(n.data[:1])
            discharge_level = None if discharge_level == 0 else discharge_level
            discharge_next_level = ord(n.data[1:2])
            battery_status = ord(n.data[2:3])
            status.set_battery_info(discharge_level, _hidpp20.BATTERY_STATUS[battery_status], discharge_next_level)
        elif n.address == 0x10:
            if _log.isEnabledFor(_INFO):
                _log.info('%s: spurious BATTERY status %s', device, n)
        else:
            _log.warn('%s: unknown BATTERY %s', device, n)
        return True

    if feature == _F.BATTERY_VOLTAGE:
        if n.address == 0x00:
            battery_level, battery_status, battery_voltage, _ignore, _ignore = _hidpp20.decipher_voltage(n.data)
            status.set_battery_info(battery_level, battery_status, None, battery_voltage)
        else:
            _log.warn('%s: unknown VOLTAGE %s', device, n)
        return True

    if feature == _F.UNIFIED_BATTERY:
        if n.address == 0x00:
            battery_level, battery_status, battery_voltage = _hidpp20.decipher_unified_battery(n.data)
            status.set_battery_info(battery_level, battery_status, None, battery_voltage)
        else:
            _log.warn('%s: unknown UNIFIED BATTERY %s', device, n)
        return True

    if feature == _F.SOLAR_DASHBOARD:
        if n.data[5:9] == b'GOOD':
            charge, lux, adc = _unpack('!BHH', n.data[:5])
            # guesstimate the battery voltage, emphasis on 'guess'
            # status_text = '%1.2fV' % (adc * 2.67793237653 / 0x0672)
            status_text = _hidpp20.BATTERY_STATUS.discharging

            if n.address == 0x00:
                status[_K.LIGHT_LEVEL] = None
                status.set_battery_info(charge, status_text, None)
            elif n.address == 0x10:
                status[_K.LIGHT_LEVEL] = lux
                if lux > 200:
                    status_text = _hidpp20.BATTERY_STATUS.recharging
                status.set_battery_info(charge, status_text, None)
            elif n.address == 0x20:
                if _log.isEnabledFor(_DEBUG):
                    _log.debug('%s: Light Check button pressed', device)
                status.changed(alert=_ALERT.SHOW_WINDOW)
                # first cancel any reporting
                # device.feature_request(_F.SOLAR_DASHBOARD)
                # trigger a new report chain
                reports_count = 15
                reports_period = 2  # seconds
                device.feature_request(_F.SOLAR_DASHBOARD, 0x00, reports_count, reports_period)
            else:
                _log.warn('%s: unknown SOLAR CHARGE %s', device, n)
        else:
            _log.warn('%s: SOLAR CHARGE not GOOD? %s', device, n)
        return True

    if feature == _F.WIRELESS_DEVICE_STATUS:
        if n.address == 0x00:
            if _log.isEnabledFor(_DEBUG):
                _log.debug('wireless status: %s', n)
            reason = 'powered on' if n.data[2] == 1 else None
            if n.data[1] == 1:  # device is asking for software reconfiguration so need to change status
                # only show a user notification if the device can change hosts
                # as we want to notify when a device changes to this host
                # but the only indication we get is this notification
                alert = _ALERT.NOTIFICATION if _F.CHANGE_HOST in device.features else _ALERT.NONE
                status.changed(active=True, alert=alert, reason=reason)
            else:
                _log.warn('%s: unknown WIRELESS %s', device, n)
        else:
            _log.warn('%s: unknown WIRELESS %s', device, n)
        return True

    if feature == _F.TOUCHMOUSE_RAW_POINTS:
        if n.address == 0x00:
            if _log.isEnabledFor(_INFO):
                _log.info('%s: TOUCH MOUSE points %s', device, n)
        elif n.address == 0x10:
            touch = ord(n.data[:1])
            button_down = bool(touch & 0x02)
            mouse_lifted = bool(touch & 0x01)
            if _log.isEnabledFor(_INFO):
                _log.info('%s: TOUCH MOUSE status: button_down=%s mouse_lifted=%s', device, button_down, mouse_lifted)
        else:
            _log.warn('%s: unknown TOUCH MOUSE %s', device, n)

    # TODO: what are REPROG_CONTROLS_V{2,3}?
    elif feature == _F.REPROG_CONTROLS:
        if n.address == 0x00:
            if _log.isEnabledFor(_INFO):
                _log.info('%s: reprogrammable key: %s', device, n)
        else:
            _log.warn('%s: unknown REPROG_CONTROLS %s', device, n)

    elif feature == _F.REPROG_CONTROLS_V4:
        if n.address == 0x00:
            if _log.isEnabledFor(_DEBUG):
                cid1, cid2, cid3, cid4 = _unpack('!HHHH', n.data[:8])
                _log.debug('%s: diverted controls pressed: %i, %i, %i, %i', device, cid1, cid2, cid3, cid4)
        elif n.address == 0x10:
            if _log.isEnabledFor(_DEBUG):
                dx, dy = _unpack('!hh', n.data[:4])
                _log.debug('%s: rawXY dx=%i dy=%i', device, dx, dy)
        elif n.address == 0x20:
            if _log.isEnabledFor(_DEBUG):
                _log.debug('%s: received analyticsKeyEvents', device)
        elif _log.isEnabledFor(_WARNING):
            _log.warn('%s: unknown REPROG_CONTROLS_V4 %s', device, n)

    elif feature == _F.HIRES_WHEEL:
        if (n.address == 0x00):
            if _log.isEnabledFor(_INFO):
                flags, delta_v = _unpack('>bh', n.data[:3])
                high_res = (flags & 0x10) != 0
                periods = flags & 0x0f
                _log.info('%s: WHEEL: res: %d periods: %d delta V:%-3d', device, high_res, periods, delta_v)
        elif (n.address == 0x10):
            if _log.isEnabledFor(_INFO):
                flags = ord(n.data[:1])
                ratchet = flags & 0x01
                _log.info('%s: WHEEL: ratchet: %d', device, ratchet)
        else:
            _log.warn('%s: unknown WHEEL %s', device, n)

    _diversion.process_notification(device, status, n, feature)

    if _log.isEnabledFor(_DEBUG):
        _log.debug('%s: notification for feature %r, report %s, data %s', device, feature, n.sub_id >> 4, _strhex(n.data))
