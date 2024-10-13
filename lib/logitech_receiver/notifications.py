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

# Handles incoming events from the receiver/devices, updating the object as appropriate.

import logging
import struct
import threading
import typing

from typing import

from solaar.i18n import _

from . import base
from . import common
from . import diversion
from . import hidpp10
from . import hidpp10_constants
from . import hidpp20
from . import hidpp20_constants
from . import settings_templates
from .common import Alert
from .common import BatteryStatus
from .common import Notification
from .hidpp10_constants import Registers

if typing.TYPE_CHECKING:
    from .base import HIDPPNotification
    from .receiver import Receiver


logger = logging.getLogger(__name__)

_hidpp10 = hidpp10.Hidpp10()
_hidpp20 = hidpp20.Hidpp20()
_F = hidpp20_constants.FEATURE


notification_lock = threading.Lock()


def process(device, notification):
    assert device
    assert notification

    if not device.isDevice:
        return _process_receiver_notification(device, notification)
    return _process_device_notification(device, notification)


def _process_receiver_notification(receiver: "Receiver", hidpp_notification: "HIDPPNotification") -> Optional[bool]:
    # supposedly only 0x4x notifications arrive for the receiver
    assert hidpp_notification.sub_id in [
        Notification.CONNECT_DISCONNECT,
        Notification.DJ_PAIRING,
        Notification.CONNECTED,
        Notification.RAW_INPUT,
        Notification.PAIRING_LOCK,
        Notification.POWER,
        Registers.DEVICE_DISCOVERY_NOTIFICATION,
        Registers.DISCOVERY_STATUS_NOTIFICATION,
        Registers.PAIRING_STATUS_NOTIFICATION,
        Registers.PASSKEY_PRESSED_NOTIFICATION,
        Registers.PASSKEY_REQUEST_NOTIFICATION,
    ]

    if hidpp_notification.sub_id == Notification.PAIRING_LOCK:
        receiver.pairing.lock_open = bool(hidpp_notification.address & 0x01)
        reason = _("pairing lock is open") if receiver.pairing.lock_open else _("pairing lock is closed")
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: %s", receiver, reason)
        receiver.pairing.error = None
        if receiver.pairing.lock_open:
            receiver.pairing.new_device = None
        pair_error = ord(hidpp_notification.data[:1])
        if pair_error:
            receiver.pairing.error = error_string = hidpp10_constants.PAIRING_ERRORS[pair_error]
            receiver.pairing.new_device = None
            logger.warning("pairing error %d: %s", pair_error, error_string)
        receiver.changed(reason=reason)
        return True

    elif hidpp_notification.sub_id == Registers.DISCOVERY_STATUS_NOTIFICATION:  # Bolt pairing
        with notification_lock:
            receiver.pairing.discovering = hidpp_notification.address == 0x00
            reason = _("discovery lock is open") if receiver.pairing.discovering else _("discovery lock is closed")
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: %s", receiver, reason)
            receiver.pairing.error = None
            if receiver.pairing.discovering:
                receiver.pairing.counter = receiver.pairing.device_address = None
                receiver.pairing.device_authentication = receiver.pairing.device_name = None
            receiver.pairing.device_passkey = None
            discover_error = ord(hidpp_notification.data[:1])
            if discover_error:
                receiver.pairing.error = discover_string = hidpp10_constants.BOLT_PAIRING_ERRORS[discover_error]
                logger.warning("bolt discovering error %d: %s", discover_error, discover_string)
            receiver.changed(reason=reason)
            return True

    elif hidpp_notification.sub_id == Registers.DEVICE_DISCOVERY_NOTIFICATION:  # Bolt pairing
        with notification_lock:
            counter = hidpp_notification.address + hidpp_notification.data[0] * 256  # notification counter
            if receiver.pairing.counter is None:
                receiver.pairing.counter = counter
            else:
                if not receiver.pairing.counter == counter:
                    return None
            if hidpp_notification.data[1] == 0:
                receiver.pairing.device_kind = hidpp_notification.data[3]
                receiver.pairing.device_address = hidpp_notification.data[6:12]
                receiver.pairing.device_authentication = hidpp_notification.data[14]
            elif hidpp_notification.data[1] == 1:
                receiver.pairing.device_name = hidpp_notification.data[3 : 3 + hidpp_notification.data[2]].decode("utf-8")
            return True

    elif hidpp_notification.sub_id == Registers.PAIRING_STATUS_NOTIFICATION:  # Bolt pairing
        with notification_lock:
            receiver.pairing.device_passkey = None
            receiver.pairing.lock_open = hidpp_notification.address == 0x00
            reason = _("pairing lock is open") if receiver.pairing.lock_open else _("pairing lock is closed")
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: %s", receiver, reason)
            receiver.pairing.error = None
            if not receiver.pairing.lock_open:
                receiver.pairing.counter = None
                receiver.pairing.device_address = None
                receiver.pairing.device_authentication = None
                receiver.pairing.device_name = None
            pair_error = hidpp_notification.data[0]
            if receiver.pairing.lock_open:
                receiver.pairing.new_device = None
            elif hidpp_notification.address == 0x02 and not pair_error:
                receiver.pairing.new_device = receiver.register_new_device(hidpp_notification.data[7])
            if pair_error:
                receiver.pairing.error = error_string = hidpp10_constants.BOLT_PAIRING_ERRORS[pair_error]
                receiver.pairing.new_device = None
                logger.warning("pairing error %d: %s", pair_error, error_string)
            receiver.changed(reason=reason)
            return True

    elif hidpp_notification.sub_id == Registers.PASSKEY_REQUEST_NOTIFICATION:  # Bolt pairing
        with notification_lock:
            receiver.pairing.device_passkey = hidpp_notification.data[0:6].decode("utf-8")
            return True

    elif hidpp_notification.sub_id == Registers.PASSKEY_PRESSED_NOTIFICATION:  # Bolt pairing
        return True

    logger.warning("%s: unhandled notification %s", receiver, hidpp_notification)


def _process_device_notification(device, n):
    # incoming packets with SubId >= 0x80 are supposedly replies from HID++ 1.0 requests, should never get here
    assert n.sub_id & 0x80 == 0

    if n.sub_id == Notification.NO_OPERATION:
        # dispose it
        return False

    # Allow the device object to handle the notification using custom per-device state.
    handling_ret = device.handle_notification(n)
    if handling_ret is not None:
        return handling_ret

    # 0x40 to 0x7F appear to be HID++ 1.0 or DJ notifications
    if n.sub_id >= 0x40:
        if n.report_id == base.DJ_MESSAGE_ID:
            return _process_dj_notification(device, n)
        else:
            return _process_hidpp10_notification(device, n)

    # These notifications are from the device itself, so it must be active
    device.online = True
    # At this point, we need to know the device's protocol, otherwise it's possible to not know how to handle it.
    assert device.protocol is not None

    # some custom battery events for HID++ 1.0 devices
    if device.protocol < 2.0:
        return _process_hidpp10_custom_notification(device, n)

    # assuming 0x00 to 0x3F are feature (HID++ 2.0) notifications
    if not device.features:
        logger.warning("%s: feature notification but features not set up: %02X %s", device, n.sub_id, n)
        return False
    try:
        feature = device.features.get_feature(n.sub_id)
    except IndexError:
        logger.warning("%s: notification from invalid feature index %02X: %s", device, n.sub_id, n)
        return False

    return _process_feature_notification(device, n, feature)


def _process_dj_notification(device, n):
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s (%s) DJ %s", device, device.protocol, n)

    if n.sub_id == Notification.CONNECT_DISCONNECT:
        # do all DJ paired notifications also show up as HID++ 1.0 notifications?
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: ignoring DJ unpaired: %s", device, n)
        return True

    if n.sub_id == Notification.DJ_PAIRING:
        # do all DJ paired notifications also show up as HID++ 1.0 notifications?
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: ignoring DJ paired: %s", device, n)
        return True

    if n.sub_id == Notification.CONNECTED:
        connected = not n.address & 0x01
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: DJ connection: %s %s", device, connected, n)
        device.changed(active=connected, alert=Alert.NONE, reason=_("connected") if connected else _("disconnected"))
        return True

    logger.warning("%s: unrecognized DJ %s", device, n)


def _process_hidpp10_custom_notification(device, n):
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s (%s) custom notification %s", device, device.protocol, n)

    if n.sub_id in (Registers.BATTERY_STATUS, Registers.BATTERY_CHARGE):
        assert n.data[-1:] == b"\x00"
        data = chr(n.address).encode() + n.data
        device.set_battery_info(hidpp10.parse_battery_status(n.sub_id, data))
        return True

    logger.warning("%s: unrecognized %s", device, n)


def _process_hidpp10_notification(device, n):
    if n.sub_id == Notification.CONNECT_DISCONNECT:  # device unpairing
        if n.address == 0x02:
            # device un-paired
            device.wpid = None
            if device.number in device.receiver:
                del device.receiver[device.number]
            device.changed(active=False, alert=Alert.ALL, reason=_("unpaired"))
        ##            device.status = None
        else:
            logger.warning("%s: disconnection with unknown type %02X: %s", device, n.address, n)
        return True

    if n.sub_id == Notification.DJ_PAIRING:  # device connection (and disconnection)
        flags = ord(n.data[:1]) & 0xF0
        if n.address == 0x02:  # very old 27 MHz protocol
            wpid = "00" + common.strhex(n.data[2:3])
            link_established = True
            link_encrypted = bool(flags & 0x80)
        elif n.address > 0x00:  # all other protocols are supposed to be almost the same
            wpid = common.strhex(n.data[2:3] + n.data[1:2])
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
        device.link_encrypted = link_encrypted
        if not link_established and device.receiver:
            hidpp10.set_configuration_pending_flags(device.receiver, 0xFF)
        device.changed(active=link_established)
        return True

    if n.sub_id == Notification.RAW_INPUT:
        # raw input event? just ignore it
        # if n.address == 0x01, no idea what it is, but they keep on coming
        # if n.address == 0x03, appears to be an actual input event, because they only come when input happents
        return True

    if n.sub_id == Notification.POWER:
        if n.address == 0x01:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: device powered on", device)
            reason = device.status_string() or _("powered on")
            device.changed(active=True, alert=Alert.NOTIFICATION, reason=reason)
        else:
            logger.warning("%s: unknown %s", device, n)
        return True

    logger.warning("%s: unrecognized %s", device, n)


def _process_feature_notification(device, n, feature):
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "%s: notification for feature %s, report %s, data %s", device, feature, n.address >> 4, common.strhex(n.data)
        )

    if feature == _F.BATTERY_STATUS:
        if n.address == 0x00:
            device.set_battery_info(hidpp20.decipher_battery_status(n.data)[1])
        elif n.address == 0x10:
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: spurious BATTERY status %s", device, n)
        else:
            logger.warning("%s: unknown BATTERY %s", device, n)

    elif feature == _F.BATTERY_VOLTAGE:
        if n.address == 0x00:
            device.set_battery_info(hidpp20.decipher_battery_voltage(n.data)[1])
        else:
            logger.warning("%s: unknown VOLTAGE %s", device, n)

    elif feature == _F.UNIFIED_BATTERY:
        if n.address == 0x00:
            device.set_battery_info(hidpp20.decipher_battery_unified(n.data)[1])
        else:
            logger.warning("%s: unknown UNIFIED BATTERY %s", device, n)

    elif feature == _F.ADC_MEASUREMENT:
        if n.address == 0x00:
            result = hidpp20.decipher_adc_measurement(n.data)
            if result:
                device.set_battery_info(result[1])
            else:  # this feature is used to signal device becoming inactive
                device.changed(active=False)
        else:
            logger.warning("%s: unknown ADC MEASUREMENT %s", device, n)

    elif feature == _F.SOLAR_DASHBOARD:
        if n.data[5:9] == b"GOOD":
            charge, lux, adc = struct.unpack("!BHH", n.data[:5])
            # guesstimate the battery voltage, emphasis on 'guess'
            # status_text = '%1.2fV' % (adc * 2.67793237653 / 0x0672)
            status_text = BatteryStatus.DISCHARGING
            if n.address == 0x00:
                device.set_battery_info(common.Battery(charge, None, status_text, None))
            elif n.address == 0x10:
                if lux > 200:
                    status_text = BatteryStatus.RECHARGING
                device.set_battery_info(common.Battery(charge, None, status_text, None, lux))
            elif n.address == 0x20:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("%s: Light Check button pressed", device)
                device.changed(alert=Alert.SHOW_WINDOW)
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
                alert = Alert.NONE
                device.changed(active=True, alert=alert, reason=reason, push=True)
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
            level = struct.unpack("!B", n.data[1:2])[0]
            if device.setting_callback:
                device.setting_callback(device, settings_templates.Backlight2Level, [level])

    elif feature == _F.REPROG_CONTROLS_V4:
        if n.address == 0x00:
            if logger.isEnabledFor(logging.DEBUG):
                cid1, cid2, cid3, cid4 = struct.unpack("!HHHH", n.data[:8])
                logger.debug("%s: diverted controls pressed: 0x%x, 0x%x, 0x%x, 0x%x", device, cid1, cid2, cid3, cid4)
        elif n.address == 0x10:
            if logger.isEnabledFor(logging.DEBUG):
                dx, dy = struct.unpack("!hh", n.data[:4])
                logger.debug("%s: rawXY dx=%i dy=%i", device, dx, dy)
        elif n.address == 0x20:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: received analyticsKeyEvents", device)
        elif logger.isEnabledFor(logging.INFO):
            logger.info("%s: unknown REPROG_CONTROLS_V4 %s", device, n)

    elif feature == _F.HIRES_WHEEL:
        if n.address == 0x00:
            if logger.isEnabledFor(logging.INFO):
                flags, delta_v = struct.unpack(">bh", n.data[:3])
                high_res = (flags & 0x10) != 0
                periods = flags & 0x0F
                logger.info("%s: WHEEL: res: %d periods: %d delta V:%-3d", device, high_res, periods, delta_v)
        elif n.address == 0x10:
            ratchet = n.data[0]
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: WHEEL: ratchet: %d", device, ratchet)
            if ratchet < 2:  # don't process messages with unusual ratchet values
                if device.setting_callback:
                    device.setting_callback(device, settings_templates.ScrollRatchet, [2 if ratchet else 1])
        else:
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: unknown WHEEL %s", device, n)

    elif feature == _F.ONBOARD_PROFILES:
        if n.address > 0x10:
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: unknown ONBOARD PROFILES %s", device, n)
        else:
            if n.address == 0x00:
                profile_sector = struct.unpack("!H", n.data[:2])[0]
                if profile_sector:
                    settings_templates.profile_change(device, profile_sector)
            elif n.address == 0x10:
                resolution_index = struct.unpack("!B", n.data[:1])[0]
                profile_sector = struct.unpack("!H", device.feature_request(_F.ONBOARD_PROFILES, 0x40)[:2])[0]
                if device.setting_callback:
                    for profile in device.profiles.profiles.values() if device.profiles else []:
                        if profile.sector == profile_sector:
                            device.setting_callback(
                                device, settings_templates.AdjustableDpi, [profile.resolutions[resolution_index]]
                            )
                            break

    elif feature == _F.BRIGHTNESS_CONTROL:
        if n.address > 0x10:
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: unknown BRIGHTNESS CONTROL %s", device, n)
        else:
            if n.address == 0x00:
                brightness = struct.unpack("!H", n.data[:2])[0]
                device.setting_callback(device, settings_templates.BrightnessControl, [brightness])
            elif n.address == 0x10:
                brightness = n.data[0] & 0x01
                if brightness:
                    brightness = struct.unpack("!H", device.feature_request(_F.BRIGHTNESS_CONTROL, 0x10)[:2])[0]
                device.setting_callback(device, settings_templates.BrightnessControl, [brightness])

    diversion.process_notification(device, n, feature)
    return True
