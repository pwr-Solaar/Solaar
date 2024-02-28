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

# Handles incoming events from the receiver/devices, updating the related
# status object as appropriate.

import logging
import threading as _threading

from struct import unpack as _unpack

from . import diversion as _diversion
from . import hidpp10 as _hidpp10
from . import hidpp10_constants as _hidpp10_constants
from . import hidpp20 as _hidpp20
from . import hidpp20_constants as _hidpp20_constants
from . import settings_templates as _st
from .base import DJ_MESSAGE_ID as _DJ_MESSAGE_ID
from .common import BATTERY_STATUS as _BATTERY_STATUS
from .common import strhex as _strhex
from .i18n import _
from .status import ALERT as _ALERT
from .status import KEYS as _K

logger = logging.getLogger(__name__)

_R = _hidpp10.REGISTERS
_R = _hidpp10_constants.REGISTERS
_F = _hidpp20_constants.FEATURE


notification_lock = _threading.Lock()


def process(device, notification):
    assert device
    assert notification

    assert hasattr(device, "status")
    status = device.status
    assert status is not None

    if not device.isDevice:
        return _process_receiver_notification(device, status, notification)

    return _process_device_notification(device, status, notification)


def _process_receiver_notification(receiver, status, n):
    # supposedly only 0x4x notifications arrive for the receiver
    assert n.sub_id & 0x40 == 0x40

    if n.sub_id == 0x4A:  # pairing lock notification
        status.lock_open = bool(n.address & 0x01)
        reason = _("pairing lock is open") if status.lock_open else _("pairing lock is closed")
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: %s", receiver, reason)
        status[_K.ERROR] = None
        if status.lock_open:
            status.new_device = None
        pair_error = ord(n.data[:1])
        if pair_error:
            status[_K.ERROR] = error_string = _hidpp10_constants.PAIRING_ERRORS[pair_error]
            status.new_device = None
            logger.warning("pairing error %d: %s", pair_error, error_string)
        status.changed(reason=reason)
        return True

    elif n.sub_id == _R.discovery_status_notification:  # Bolt pairing
        with notification_lock:
            status.discovering = n.address == 0x00
            reason = _("discovery lock is open") if status.discovering else _("discovery lock is closed")
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: %s", receiver, reason)
            status[_K.ERROR] = None
            if status.discovering:
                status.counter = status.device_address = status.device_authentication = status.device_name = None
            status.device_passkey = None
            discover_error = ord(n.data[:1])
            if discover_error:
                status[_K.ERROR] = discover_string = _hidpp10_constants.BOLT_PAIRING_ERRORS[discover_error]
                logger.warning("bolt discovering error %d: %s", discover_error, discover_string)
            status.changed(reason=reason)
            return True

    elif n.sub_id == _R.device_discovery_notification:  # Bolt pairing
        with notification_lock:
            counter = n.address + n.data[0] * 256  # notification counter
            if status.counter is None:
                status.counter = counter
            else:
                if not status.counter == counter:
                    return None
            if n.data[1] == 0:
                status.device_kind = n.data[3]
                status.device_address = n.data[6:12]
                status.device_authentication = n.data[14]
            elif n.data[1] == 1:
                status.device_name = n.data[3 : 3 + n.data[2]].decode("utf-8")
            return True

    elif n.sub_id == _R.pairing_status_notification:  # Bolt pairing
        with notification_lock:
            status.device_passkey = None
            status.lock_open = n.address == 0x00
            reason = _("pairing lock is open") if status.lock_open else _("pairing lock is closed")
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: %s", receiver, reason)
            status[_K.ERROR] = None
            if not status.lock_open:
                status.counter = status.device_address = status.device_authentication = status.device_name = None
            pair_error = n.data[0]
            if status.lock_open:
                status.new_device = None
            elif n.address == 0x02 and not pair_error:
                status.new_device = receiver.register_new_device(n.data[7])
            if pair_error:
                status[_K.ERROR] = error_string = _hidpp10_constants.BOLT_PAIRING_ERRORS[pair_error]
                status.new_device = None
                logger.warning("pairing error %d: %s", pair_error, error_string)
            status.changed(reason=reason)
            return True

    elif n.sub_id == _R.passkey_request_notification:  # Bolt pairing
        with notification_lock:
            status.device_passkey = n.data[0:6].decode("utf-8")
            return True

    elif n.sub_id == _R.passkey_pressed_notification:  # Bolt pairing
        return True

    logger.warning("%s: unhandled notification %s", receiver, n)


def _process_device_notification(device, status, n):
    # incoming packets with SubId >= 0x80 are supposedly replies from HID++ 1.0 requests, should never get here
    assert n.sub_id & 0x80 == 0

    if n.sub_id == 00:  # no-op feature notification, dispose of it quickly
        return False

    # Allow the device object to handle the notification using custom per-device state.
    handling_ret = device.handle_notification(n)
    if handling_ret is not None:
        return handling_ret

    # 0x40 to 0x7F appear to be HID++ 1.0 or DJ notifications
    if n.sub_id >= 0x40:
        if n.report_id == _DJ_MESSAGE_ID:
            return _process_dj_notification(device, status, n)
        else:
            return _process_hidpp10_notification(device, status, n)

    # These notifications are from the device itself, so it must be active
    device.online = True
    # At this point, we need to know the device's protocol, otherwise it's possible to not know how to handle it.
    assert device.protocol is not None

    # some custom battery events for HID++ 1.0 devices
    if device.protocol < 2.0:
        return _process_hidpp10_custom_notification(device, status, n)

    # assuming 0x00 to 0x3F are feature (HID++ 2.0) notifications
    if not device.features:
        logger.warning("%s: feature notification but features not set up: %02X %s", device, n.sub_id, n)
        return False
    try:
        feature = device.features.get_feature(n.sub_id)
    except IndexError:
        logger.warning("%s: notification from invalid feature index %02X: %s", device, n.sub_id, n)
        return False

    return _process_feature_notification(device, status, n, feature)


def _process_dj_notification(device, status, n):
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s (%s) DJ %s", device, device.protocol, n)

    if n.sub_id == 0x40:
        # do all DJ paired notifications also show up as HID++ 1.0 notifications?
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: ignoring DJ unpaired: %s", device, n)
        return True

    if n.sub_id == 0x41:
        # do all DJ paired notifications also show up as HID++ 1.0 notifications?
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: ignoring DJ paired: %s", device, n)
        return True

    if n.sub_id == 0x42:
        connected = not n.address & 0x01
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: DJ connection: %s %s", device, connected, n)
        status.changed(active=connected, alert=_ALERT.NONE, reason=_("connected") if connected else _("disconnected"))
        return True

    logger.warning("%s: unrecognized DJ %s", device, n)


def _process_hidpp10_custom_notification(device, status, n):
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s (%s) custom notification %s", device, device.protocol, n)

    if n.sub_id in (_R.battery_status, _R.battery_charge):
        # message layout: 10 ix <register> <xx> <yy> <zz> <00>
        assert n.data[-1:] == b"\x00"
        data = chr(n.address).encode() + n.data
        charge, next_charge, status_text, voltage = _hidpp10.parse_battery_status(n.sub_id, data)
        status.set_battery_info(charge, next_charge, status_text, voltage)
        return True

    logger.warning("%s: unrecognized %s", device, n)


def _process_hidpp10_notification(device, status, n):
    if n.sub_id == 0x40:  # device unpairing
        if n.address == 0x02:
            # device un-paired
            status.clear()
            device.wpid = None
            device.status = None
            if device.number in device.receiver:
                del device.receiver[device.number]
            status.changed(active=False, alert=_ALERT.ALL, reason=_("unpaired"))
        else:
            logger.warning("%s: disconnection with unknown type %02X: %s", device, n.address, n)
        return True

    if n.sub_id == 0x41:  # device connection (and disconnection)
        flags = ord(n.data[:1]) & 0xF0
        if n.address == 0x02:  # very old 27 MHz protocol
            wpid = "00" + _strhex(n.data[2:3])
            link_established = True
            link_encrypted = bool(flags & 0x80)
        elif n.address > 0x00:  # all other protocols are supposed to be almost the same
            wpid = _strhex(n.data[2:3] + n.data[1:2])
            link_established = not (flags & 0x40)
            link_encrypted = bool(flags & 0x20) or n.address == 0x10  # Bolt protocol always encrypted
        else:
            logger.warning("%s: connection notification with unknown protocol %02X: %s", device.number, n.address, n)
            return True
        if wpid != device.wpid:
            logger.warning("%s wpid mismatch, got %s", device, wpid)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "%s: protocol %s connection notification: software=%s, encrypted=%s, link=%s, payload=%s",
                device,
                n.address,
                bool(flags & 0x10),
                link_encrypted,
                link_established,
                bool(flags & 0x80),
            )
        status[_K.LINK_ENCRYPTED] = link_encrypted
        status.changed(active=link_established)
        return True

    if n.sub_id == 0x49:
        # raw input event? just ignore it
        # if n.address == 0x01, no idea what it is, but they keep on coming
        # if n.address == 0x03, appears to be an actual input event, because they only come when input happents
        return True

    if n.sub_id == 0x4B:  # power notification
        if n.address == 0x01:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: device powered on", device)
            reason = status.to_string() or _("powered on")
            status.changed(active=True, alert=_ALERT.NOTIFICATION, reason=reason)
        else:
            logger.warning("%s: unknown %s", device, n)
        return True

    logger.warning("%s: unrecognized %s", device, n)


def _process_feature_notification(device, status, n, feature):
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s: notification for feature %s, report %s, data %s", device, feature, n.address >> 4, _strhex(n.data))

    if feature == _F.BATTERY_STATUS:
        if n.address == 0x00:
            _ignore, discharge_level, discharge_next_level, battery_status, voltage = _hidpp20.decipher_battery_status(n.data)
            status.set_battery_info(discharge_level, discharge_next_level, battery_status, voltage)
        elif n.address == 0x10:
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: spurious BATTERY status %s", device, n)
        else:
            logger.warning("%s: unknown BATTERY %s", device, n)

    elif feature == _F.BATTERY_VOLTAGE:
        if n.address == 0x00:
            _ignore, level, nextl, battery_status, voltage = _hidpp20.decipher_battery_voltage(n.data)
            status.set_battery_info(level, nextl, battery_status, voltage)
        else:
            logger.warning("%s: unknown VOLTAGE %s", device, n)

    elif feature == _F.UNIFIED_BATTERY:
        if n.address == 0x00:
            _ignore, level, nextl, battery_status, voltage = _hidpp20.decipher_battery_unified(n.data)
            status.set_battery_info(level, nextl, battery_status, voltage)
        else:
            logger.warning("%s: unknown UNIFIED BATTERY %s", device, n)

    elif feature == _F.ADC_MEASUREMENT:
        if n.address == 0x00:
            result = _hidpp20.decipher_adc_measurement(n.data)
            if result:
                _ignore, level, nextl, battery_status, voltage = result
                status.set_battery_info(level, nextl, battery_status, voltage)
            else:  # this feature is used to signal device becoming inactive
                status.changed(active=False)
        else:
            logger.warning("%s: unknown ADC MEASUREMENT %s", device, n)

    elif feature == _F.SOLAR_DASHBOARD:
        if n.data[5:9] == b"GOOD":
            charge, lux, adc = _unpack("!BHH", n.data[:5])
            # guesstimate the battery voltage, emphasis on 'guess'
            # status_text = '%1.2fV' % (adc * 2.67793237653 / 0x0672)
            status_text = _BATTERY_STATUS.discharging
            if n.address == 0x00:
                status[_K.LIGHT_LEVEL] = None
                status.set_battery_info(charge, None, status_text, None)
            elif n.address == 0x10:
                status[_K.LIGHT_LEVEL] = lux
                if lux > 200:
                    status_text = _BATTERY_STATUS.recharging
                status.set_battery_info(charge, None, status_text, None)
            elif n.address == 0x20:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("%s: Light Check button pressed", device)
                status.changed(alert=_ALERT.SHOW_WINDOW)
                # first cancel any reporting
                # device.feature_request(_F.SOLAR_DASHBOARD)
                # trigger a new report chain
                reports_count = 15
                reports_period = 2  # seconds
                device.feature_request(_F.SOLAR_DASHBOARD, 0x00, reports_count, reports_period)
            else:
                logger.warning("%s: unknown SOLAR CHARGE %s", device, n)
        else:
            logger.warning("%s: SOLAR CHARGE not GOOD? %s", device, n)

    elif feature == _F.WIRELESS_DEVICE_STATUS:
        if n.address == 0x00:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("wireless status: %s", n)
            reason = "powered on" if n.data[2] == 1 else None
            if n.data[1] == 1:  # device is asking for software reconfiguration so need to change status
                alert = _ALERT.NONE
                status.changed(active=True, alert=alert, reason=reason, push=True)
        else:
            logger.warning("%s: unknown WIRELESS %s", device, n)

    elif feature == _F.TOUCHMOUSE_RAW_POINTS:
        if n.address == 0x00:
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: TOUCH MOUSE points %s", device, n)
        elif n.address == 0x10:
            touch = ord(n.data[:1])
            button_down = bool(touch & 0x02)
            mouse_lifted = bool(touch & 0x01)
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: TOUCH MOUSE status: button_down=%s mouse_lifted=%s", device, button_down, mouse_lifted)
        else:
            logger.warning("%s: unknown TOUCH MOUSE %s", device, n)

    # TODO: what are REPROG_CONTROLS_V{2,3}?
    elif feature == _F.REPROG_CONTROLS:
        if n.address == 0x00:
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: reprogrammable key: %s", device, n)
        else:
            logger.warning("%s: unknown REPROG_CONTROLS %s", device, n)

    elif feature == _F.BACKLIGHT2:
        if n.address == 0x00:
            level = _unpack("!B", n.data[1:2])[0]
            if device.setting_callback:
                device.setting_callback(device, _st.Backlight2Level, [level])

    elif feature == _F.REPROG_CONTROLS_V4:
        if n.address == 0x00:
            if logger.isEnabledFor(logging.DEBUG):
                cid1, cid2, cid3, cid4 = _unpack("!HHHH", n.data[:8])
                logger.debug("%s: diverted controls pressed: 0x%x, 0x%x, 0x%x, 0x%x", device, cid1, cid2, cid3, cid4)
        elif n.address == 0x10:
            if logger.isEnabledFor(logging.DEBUG):
                dx, dy = _unpack("!hh", n.data[:4])
                logger.debug("%s: rawXY dx=%i dy=%i", device, dx, dy)
        elif n.address == 0x20:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: received analyticsKeyEvents", device)
        elif logger.isEnabledFor(logging.INFO):
            logger.info("%s: unknown REPROG_CONTROLS_V4 %s", device, n)

    elif feature == _F.HIRES_WHEEL:
        if n.address == 0x00:
            if logger.isEnabledFor(logging.INFO):
                flags, delta_v = _unpack(">bh", n.data[:3])
                high_res = (flags & 0x10) != 0
                periods = flags & 0x0F
                logger.info("%s: WHEEL: res: %d periods: %d delta V:%-3d", device, high_res, periods, delta_v)
        elif n.address == 0x10:
            ratchet = n.data[0]
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: WHEEL: ratchet: %d", device, ratchet)
            if ratchet < 2:  # don't process messages with unusual ratchet values
                if device.setting_callback:
                    device.setting_callback(device, _st.ScrollRatchet, [2 if ratchet else 1])
        else:
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: unknown WHEEL %s", device, n)

    elif feature == _F.ONBOARD_PROFILES:
        if n.address > 0x10:
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: unknown ONBOARD PROFILES %s", device, n)
        else:
            if n.address == 0x00:
                profile_sector = _unpack("!H", n.data[:2])[0]
                if profile_sector:
                    _st.profile_change(device, profile_sector)
            elif n.address == 0x10:
                resolution_index = _unpack("!B", n.data[:1])[0]
                profile_sector = _unpack("!H", device.feature_request(_F.ONBOARD_PROFILES, 0x40)[:2])[0]
                if device.setting_callback:
                    for profile in device.profiles.profiles.values() if device.profiles else []:
                        if profile.sector == profile_sector:
                            device.setting_callback(device, _st.AdjustableDpi, [profile.resolutions[resolution_index]])
                            break

    _diversion.process_notification(device, status, n, feature)
    return True
