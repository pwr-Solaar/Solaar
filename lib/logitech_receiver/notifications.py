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

"""Handles incoming events from the receiver/devices, updating the
object as appropriate.
"""

from __future__ import annotations

import logging
import struct
import threading
import typing

from solaar.i18n import _

from . import base
from . import common
from . import diversion
from . import hidpp10
from . import hidpp10_constants
from . import hidpp20
from . import settings_templates
from .common import Alert
from .common import BatteryStatus
from .common import Notification
from .hidpp10_constants import Registers
from .hidpp20_constants import SupportedFeature

if typing.TYPE_CHECKING:
    from .base import HIDPPNotification
    from .device import Device
    from .receiver import Receiver

logger = logging.getLogger(__name__)

NotificationHandler = typing.Callable[["Receiver", "HIDPPNotification"], bool]

_hidpp10 = hidpp10.Hidpp10()
_hidpp20 = hidpp20.Hidpp20()

notification_lock = threading.Lock()


def process(device: Device | Receiver, notification: HIDPPNotification):
    """Handle incoming events (notification) from device or receiver."""
    assert device
    assert notification

    if not device.isDevice:
        return process_receiver_notification(device, notification)
    return process_device_notification(device, notification)


def process_receiver_notification(receiver: Receiver, notification: HIDPPNotification) -> bool | None:
    """Process event messages from receivers."""
    event_handler_mapping: dict[int, NotificationHandler] = {
        Notification.PAIRING_LOCK: handle_pairing_lock,
        Registers.DEVICE_DISCOVERY_NOTIFICATION: handle_device_discovery,
        Registers.DISCOVERY_STATUS_NOTIFICATION: handle_discovery_status,
        Registers.PAIRING_STATUS_NOTIFICATION: handle_pairing_status,
        Registers.PASSKEY_PRESSED_NOTIFICATION: handle_passkey_pressed,
        Registers.PASSKEY_REQUEST_NOTIFICATION: handle_passkey_request,
    }

    try:
        handler_func = event_handler_mapping[notification.sub_id]
        return handler_func(receiver, notification)
    except KeyError:
        pass

    assert notification.sub_id in [
        Notification.CONNECT_DISCONNECT,
        Notification.DJ_PAIRING,
        Notification.CONNECTED,
        Notification.RAW_INPUT,
        Notification.POWER,
    ]

    logger.warning(f"{receiver}: unhandled notification {notification}")


def process_device_notification(device: Device, notification: HIDPPNotification):
    """Process event messages from devices."""

    # incoming packets with SubId >= 0x80 are supposedly replies from HID++ 1.0 requests, should never get here
    assert notification.sub_id & 0x80 == 0

    if notification.sub_id == Notification.NO_OPERATION:
        # dispose it
        return False

    # Allow the device object to handle the notification using custom per-device state.
    handling_ret = device.handle_notification(notification)
    if handling_ret is not None:
        return handling_ret

    # 0x40 to 0x7F appear to be HID++ 1.0 or DJ notifications
    if notification.sub_id >= 0x40:
        if notification.report_id == base.DJ_MESSAGE_ID:
            return _process_dj_notification(device, notification)
        else:
            return _process_hidpp10_notification(device, notification)

    # These notifications are from the device itself, so it must be active
    device.online = True
    # At this point, we need to know the device's protocol, otherwise it's possible to not know how to handle it.
    assert device.protocol is not None

    # some custom battery events for HID++ 1.0 devices
    if device.protocol < 2.0:
        return _process_hidpp10_custom_notification(device, notification)

    # assuming 0x00 to 0x3F are feature (HID++ 2.0) notifications
    if not device.features:
        logger.warning("%s: feature notification but features not set up: %02X %s", device, notification.sub_id, notification)
        return False

    return _process_feature_notification(device, notification)


def _process_dj_notification(device: Device, notification: HIDPPNotification):
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s (%s) DJ %s", device, device.protocol, notification)

    if notification.sub_id == Notification.CONNECT_DISCONNECT:
        # do all DJ paired notifications also show up as HID++ 1.0 notifications?
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: ignoring DJ unpaired: %s", device, notification)
        return True

    if notification.sub_id == Notification.DJ_PAIRING:
        # do all DJ paired notifications also show up as HID++ 1.0 notifications?
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: ignoring DJ paired: %s", device, notification)
        return True

    if notification.sub_id == Notification.CONNECTED:
        connected = not notification.address & 0x01
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: DJ connection: %s %s", device, connected, notification)
        device.changed(active=connected, alert=Alert.NONE, reason=_("connected") if connected else _("disconnected"))
        return True

    logger.warning("%s: unrecognized DJ %s", device, notification)


def _process_hidpp10_custom_notification(device: Device, notification: HIDPPNotification):
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s (%s) custom notification %s", device, device.protocol, notification)

    if notification.sub_id in (Registers.BATTERY_STATUS, Registers.BATTERY_CHARGE):
        assert notification.data[-1:] == b"\x00"
        data = chr(notification.address).encode() + notification.data
        device.set_battery_info(hidpp10.parse_battery_status(notification.sub_id, data))
        return True

    logger.warning("%s: unrecognized %s", device, notification)


def _process_hidpp10_notification(device: Device, notification: HIDPPNotification):
    if notification.sub_id == Notification.CONNECT_DISCONNECT:  # device unpairing
        if notification.address == 0x02:
            # device un-paired
            device.wpid = None
            if device.number in device.receiver:
                del device.receiver[device.number]
            device.changed(active=False, alert=Alert.ALL, reason=_("unpaired"))
        ##            device.status = None
        else:
            logger.warning("%s: disconnection with unknown type %02X: %s", device, notification.address, notification)
        return True

    if notification.sub_id == Notification.DJ_PAIRING:  # device connection (and disconnection)
        flags = ord(notification.data[:1]) & 0xF0
        if notification.address == 0x02:  # very old 27 MHz protocol
            wpid = "00" + common.strhex(notification.data[2:3])
            link_established = True
            link_encrypted = bool(flags & 0x80)
        elif notification.address > 0x00:  # all other protocols are supposed to be almost the same
            wpid = common.strhex(notification.data[2:3] + notification.data[1:2])
            link_established = not (flags & 0x40)
            link_encrypted = bool(flags & 0x20) or notification.address == 0x10  # Bolt protocol always encrypted
        else:
            logger.warning(
                "%s: connection notification with unknown protocol %02X: %s", device.number, notification.address, notification
            )
            return True
        if wpid != device.wpid:
            logger.warning("%s wpid mismatch, got %s", device, wpid)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "%s: protocol %s connection notification: software=%s, encrypted=%s, link=%s, payload=%s",
                device,
                notification.address,
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

    if notification.sub_id == Notification.RAW_INPUT:
        # raw input event? just ignore it
        # if notification.address == 0x01, no idea what it is, but they keep on coming
        # if notification.address == 0x03, appears to be an actual input event, because they only come when input happents
        return True

    if notification.sub_id == Notification.POWER:
        if notification.address == 0x01:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: device powered on", device)
            reason = device.status_string() or _("powered on")
            device.changed(active=True, alert=Alert.NOTIFICATION, reason=reason)
        else:
            logger.warning("%s: unknown %s", device, notification)
        return True

    logger.warning("%s: unrecognized %s", device, notification)


def _process_feature_notification(device: Device, notification: HIDPPNotification):
    try:
        feature = device.features.get_feature(notification.sub_id)
    except IndexError:
        logger.warning("%s: notification from invalid feature index %02X: %s", device, notification.sub_id, notification)
        return False

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "%s: notification for feature %s, report %s, data %s",
            device,
            feature,
            notification.address >> 4,
            common.strhex(notification.data),
        )

    if feature == SupportedFeature.BATTERY_STATUS:
        if notification.address == 0x00:
            device.set_battery_info(hidpp20.decipher_battery_status(notification.data)[1])
        elif notification.address == 0x10:
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: spurious BATTERY status %s", device, notification)
        else:
            logger.warning("%s: unknown BATTERY %s", device, notification)

    elif feature == SupportedFeature.BATTERY_VOLTAGE:
        if notification.address == 0x00:
            device.set_battery_info(hidpp20.decipher_battery_voltage(notification.data)[1])
        else:
            logger.warning("%s: unknown VOLTAGE %s", device, notification)

    elif feature == SupportedFeature.UNIFIED_BATTERY:
        if notification.address == 0x00:
            device.set_battery_info(hidpp20.decipher_battery_unified(notification.data)[1])
        else:
            logger.warning("%s: unknown UNIFIED BATTERY %s", device, notification)

    elif feature == SupportedFeature.ADC_MEASUREMENT:
        if notification.address == 0x00:
            result = hidpp20.decipher_adc_measurement(notification.data)
            if result:
                device.set_battery_info(result[1])
            else:  # this feature is used to signal device becoming inactive
                device.changed(active=False)
        else:
            logger.warning("%s: unknown ADC MEASUREMENT %s", device, notification)

    elif feature == SupportedFeature.SOLAR_DASHBOARD:
        if notification.data[5:9] == b"GOOD":
            charge, lux, adc = struct.unpack("!BHH", notification.data[:5])
            # guesstimate the battery voltage, emphasis on 'guess'
            # status_text = '%1.2fV' % (adc * 2.67793237653 / 0x0672)
            status_text = BatteryStatus.DISCHARGING
            if notification.address == 0x00:
                device.set_battery_info(common.Battery(charge, None, status_text, None))
            elif notification.address == 0x10:
                if lux > 200:
                    status_text = BatteryStatus.RECHARGING
                device.set_battery_info(common.Battery(charge, None, status_text, None, lux))
            elif notification.address == 0x20:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("%s: Light Check button pressed", device)
                device.changed(alert=Alert.SHOW_WINDOW)
                # first cancel any reporting
                # device.feature_request(SupportedFeature.SOLAR_DASHBOARD)
                # trigger a new report chain
                reports_count = 15
                reports_period = 2  # seconds
                device.feature_request(SupportedFeature.SOLAR_DASHBOARD, 0x00, reports_count, reports_period)
            else:
                logger.warning("%s: unknown SOLAR CHARGE %s", device, notification)
        else:
            logger.warning("%s: SOLAR CHARGE not GOOD? %s", device, notification)

    elif feature == SupportedFeature.WIRELESS_DEVICE_STATUS:
        if notification.address == 0x00:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("wireless status: %s", notification)
            reason = "powered on" if notification.data[2] == 1 else None
            if notification.data[1] == 1:  # device is asking for software reconfiguration so need to change status
                alert = Alert.NONE
                device.changed(active=True, alert=alert, reason=reason, push=True)
        else:
            logger.warning("%s: unknown WIRELESS %s", device, notification)

    elif feature == SupportedFeature.TOUCHMOUSE_RAW_POINTS:
        if notification.address == 0x00:
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: TOUCH MOUSE points %s", device, notification)
        elif notification.address == 0x10:
            touch = ord(notification.data[:1])
            button_down = bool(touch & 0x02)
            mouse_lifted = bool(touch & 0x01)
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: TOUCH MOUSE status: button_down=%s mouse_lifted=%s", device, button_down, mouse_lifted)
        else:
            logger.warning("%s: unknown TOUCH MOUSE %s", device, notification)

    # TODO: what are REPROG_CONTROLS_V{2,3}?
    elif feature == SupportedFeature.REPROG_CONTROLS:
        if notification.address == 0x00:
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: reprogrammable key: %s", device, notification)
        else:
            logger.warning("%s: unknown REPROG_CONTROLS %s", device, notification)

    elif feature == SupportedFeature.BACKLIGHT2:
        if notification.address == 0x00:
            level = struct.unpack("!B", notification.data[1:2])[0]
            if device.setting_callback:
                device.setting_callback(device, settings_templates.Backlight2Level, [level])

    elif feature == SupportedFeature.REPROG_CONTROLS_V4:
        if notification.address == 0x00:
            if logger.isEnabledFor(logging.DEBUG):
                cid1, cid2, cid3, cid4 = struct.unpack("!HHHH", notification.data[:8])
                logger.debug("%s: diverted controls pressed: 0x%x, 0x%x, 0x%x, 0x%x", device, cid1, cid2, cid3, cid4)
        elif notification.address == 0x10:
            if logger.isEnabledFor(logging.DEBUG):
                dx, dy = struct.unpack("!hh", notification.data[:4])
                logger.debug("%s: rawXY dx=%i dy=%i", device, dx, dy)
        elif notification.address == 0x20:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: received analyticsKeyEvents", device)
        elif logger.isEnabledFor(logging.INFO):
            logger.info("%s: unknown REPROG_CONTROLS_V4 %s", device, notification)

    elif feature == SupportedFeature.HIRES_WHEEL:
        if notification.address == 0x00:
            if logger.isEnabledFor(logging.INFO):
                flags, delta_v = struct.unpack(">bh", notification.data[:3])
                high_res = (flags & 0x10) != 0
                periods = flags & 0x0F
                logger.info("%s: WHEEL: res: %d periods: %d delta V:%-3d", device, high_res, periods, delta_v)
        elif notification.address == 0x10:
            ratchet = notification.data[0]
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: WHEEL: ratchet: %d", device, ratchet)
            if ratchet < 2:  # don't process messages with unusual ratchet values
                if device.setting_callback:
                    device.setting_callback(device, settings_templates.ScrollRatchet, [2 if ratchet else 1])
        else:
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: unknown WHEEL %s", device, notification)

    elif feature == SupportedFeature.ONBOARD_PROFILES:
        if notification.address > 0x10:
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: unknown ONBOARD PROFILES %s", device, notification)
        else:
            if notification.address == 0x00:
                profile_sector = struct.unpack("!H", notification.data[:2])[0]
                if profile_sector:
                    settings_templates.profile_change(device, profile_sector)
            elif notification.address == 0x10:
                resolution_index = struct.unpack("!B", notification.data[:1])[0]
                profile_sector = struct.unpack("!H", device.feature_request(SupportedFeature.ONBOARD_PROFILES, 0x40)[:2])[0]
                if device.setting_callback:
                    for profile in device.profiles.profiles.values() if device.profiles else []:
                        if profile.sector == profile_sector:
                            device.setting_callback(
                                device, settings_templates.AdjustableDpi, [profile.resolutions[resolution_index]]
                            )
                            break

    elif feature == SupportedFeature.BRIGHTNESS_CONTROL:
        if notification.address > 0x10:
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: unknown BRIGHTNESS CONTROL %s", device, notification)
        else:
            if notification.address == 0x00:
                brightness = struct.unpack("!H", notification.data[:2])[0]
                device.setting_callback(device, settings_templates.BrightnessControl, [brightness])
            elif notification.address == 0x10:
                brightness = notification.data[0] & 0x01
                if brightness:
                    brightness = struct.unpack("!H", device.feature_request(SupportedFeature.BRIGHTNESS_CONTROL, 0x10)[:2])[0]
                device.setting_callback(device, settings_templates.BrightnessControl, [brightness])

    diversion.process_notification(device, notification, feature)
    return True


def handle_pairing_lock(receiver: Receiver, notification: HIDPPNotification) -> bool:
    receiver.pairing.lock_open = bool(notification.address & 0x01)
    reason = _("pairing lock is open") if receiver.pairing.lock_open else _("pairing lock is closed")
    if logger.isEnabledFor(logging.INFO):
        logger.info("%s: %s", receiver, reason)
    receiver.pairing.error = None
    if receiver.pairing.lock_open:
        receiver.pairing.new_device = None
    pair_error = ord(notification.data[:1])
    if pair_error:
        receiver.pairing.error = error_string = hidpp10_constants.PairingError(pair_error)
        receiver.pairing.new_device = None
        logger.warning("pairing error %d: %s", pair_error, error_string)
    receiver.changed(reason=reason)
    return True


def handle_discovery_status(receiver: Receiver, notification: HIDPPNotification) -> bool:
    with notification_lock:
        receiver.pairing.discovering = notification.address == 0x00
        reason = _("discovery lock is open") if receiver.pairing.discovering else _("discovery lock is closed")
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: %s", receiver, reason)
        receiver.pairing.error = None
        if receiver.pairing.discovering:
            receiver.pairing.counter = receiver.pairing.device_address = None
            receiver.pairing.device_authentication = receiver.pairing.device_name = None
        receiver.pairing.device_passkey = None
        discover_error = ord(notification.data[:1])
        if discover_error:
            receiver.pairing.error = discover_string = hidpp10_constants.BoltPairingError(discover_error)
            logger.warning("bolt discovering error %d: %s", discover_error, discover_string)
        receiver.changed(reason=reason)
        return True


def handle_device_discovery(receiver: Receiver, notification: HIDPPNotification) -> bool:
    with notification_lock:
        counter = notification.address + notification.data[0] * 256  # notification counter
        if receiver.pairing.counter is None:
            receiver.pairing.counter = counter
        else:
            if not receiver.pairing.counter == counter:
                return None
        if notification.data[1] == 0:
            receiver.pairing.device_kind = notification.data[3]
            receiver.pairing.device_address = notification.data[6:12]
            receiver.pairing.device_authentication = notification.data[14]
        elif notification.data[1] == 1:
            receiver.pairing.device_name = notification.data[3 : 3 + notification.data[2]].decode("utf-8")
        return True


def handle_pairing_status(receiver: Receiver, notification: HIDPPNotification) -> bool:
    with notification_lock:
        receiver.pairing.device_passkey = None
        receiver.pairing.lock_open = notification.address == 0x00
        reason = _("pairing lock is open") if receiver.pairing.lock_open else _("pairing lock is closed")
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: %s", receiver, reason)
        receiver.pairing.error = None
        if not receiver.pairing.lock_open:
            receiver.pairing.counter = None
            receiver.pairing.device_address = None
            receiver.pairing.device_authentication = None
            receiver.pairing.device_name = None
        pair_error = notification.data[0]
        if receiver.pairing.lock_open:
            receiver.pairing.new_device = None
        elif notification.address == 0x02 and not pair_error:
            receiver.pairing.new_device = receiver.register_new_device(notification.data[7])
        if pair_error:
            receiver.pairing.error = error_string = hidpp10_constants.BoltPairingError(pair_error)
            receiver.pairing.new_device = None
            logger.warning("pairing error %d: %s", pair_error, error_string)
        receiver.changed(reason=reason)
        return True


def handle_passkey_request(receiver: Receiver, notification: HIDPPNotification) -> bool:
    with notification_lock:
        receiver.pairing.device_passkey = notification.data[0:6].decode("utf-8")
        return True


def handle_passkey_pressed(_receiver: Receiver, _hidpp_notification: HIDPPNotification) -> bool:
    return True
