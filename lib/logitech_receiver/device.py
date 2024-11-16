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

from __future__ import annotations

import errno
import logging
import threading
import time
import typing

from typing import Callable
from typing import Optional
from typing import Protocol

from solaar import configuration

from . import descriptors
from . import exceptions
from . import hidpp10
from . import hidpp10_constants
from . import hidpp20
from . import settings
from . import settings_templates
from .common import Alert
from .common import Battery
from .hidpp10_constants import NotificationFlag
from .hidpp20_constants import SupportedFeature

if typing.TYPE_CHECKING:
    from logitech_receiver import common

logger = logging.getLogger(__name__)

_hidpp10 = hidpp10.Hidpp10()
_hidpp20 = hidpp20.Hidpp20()


class LowLevelInterface(Protocol):
    def open_path(self, path) -> int:
        ...

    def find_paired_node(self, receiver_path: str, index: int, timeout: int):
        ...

    def ping(self, handle, number, long_message: bool):
        ...

    def request(self, handle, devnumber, request_id, *params, **kwargs):
        ...

    def close(self, handle, *args, **kwargs) -> bool:
        ...


def create_device(low_level: LowLevelInterface, device_info, setting_callback=None):
    """Opens a Logitech Device found attached to the machine, by Linux device path.
    :returns: An open file handle for the found receiver, or None.
    """
    try:
        handle = low_level.open_path(device_info.path)
        if handle:
            # a direct connected device might not be online (as reported by user)
            return Device(
                low_level,
                None,
                None,
                None,
                handle=handle,
                device_info=device_info,
                setting_callback=setting_callback,
            )
    except OSError as e:
        logger.exception("open %s", device_info)
        if e.errno == errno.EACCES:
            raise
    except Exception:
        logger.exception("open %s", device_info)
        raise


class Device:
    instances = []
    read_register: Callable = hidpp10.read_register
    write_register: Callable = hidpp10.write_register

    def __init__(
        self,
        low_level: LowLevelInterface,
        receiver,
        number,
        online,
        pairing_info=None,
        handle=None,
        device_info=None,
        setting_callback=None,
    ):
        assert receiver or device_info
        if receiver:
            assert 0 < number <= 15  # some receivers have devices past their max # of devices
        self.low_level = low_level
        self.number = number  # will be None at this point for directly connected devices
        self.online = online  # is the device online? - gates many atempts to contact the device
        self.descriptor = None
        self.isDevice = True  # some devices act as receiver so we need a property to distinguish them
        self.may_unpair = False
        self.receiver = receiver
        self.handle = handle
        self.path = device_info.path if device_info else None
        self.product_id = device_info.product_id if device_info else None
        self.hidpp_short = device_info.hidpp_short if device_info else None
        self.hidpp_long = device_info.hidpp_long if device_info else None
        self.bluetooth = device_info.bus_id == 0x0005 if device_info else False  # Bluetooth needs long messages
        self.hid_serial = device_info.serial if device_info else None
        self.setting_callback = setting_callback  # for changes to settings
        self.status_callback = None  # for changes to other potentially visible aspects
        self.wpid = pairing_info["wpid"] if pairing_info else None  # the Wireless PID is unique per device model
        self._kind = pairing_info["kind"] if pairing_info else None  # mouse, keyboard, etc (see hidpp10.DEVICE_KIND)
        self._serial = pairing_info["serial"] if pairing_info else None  # serial number (an 8-char hex string)
        self._polling_rate = pairing_info["polling"] if pairing_info else None
        self._power_switch = pairing_info["power_switch"] if pairing_info else None
        self._name = None  # the full name of the model
        self._codename = None  # Unifying peripherals report a codename.
        self._protocol = None  # HID++ protocol version, 1.0 or 2.0
        self._unitId = None  # unit id (distinguishes within a model - generally the same as serial)
        self._modelId = None  # model id (contains identifiers for the transports of the device)
        self._tid_map = None  # map from transports to product identifiers
        self._persister = None  # persister holds settings
        self._led_effects = self._firmware = self._keys = self._remap_keys = self._gestures = None
        self._profiles = self._backlight = self._settings = None
        self.registers = []
        self.notification_flags = None
        self.battery_info = None
        self.link_encrypted = None
        self._active = None  # lags self.online - is used to help determine when to setup devices

        self._feature_settings_checked = False
        self._gestures_lock = threading.Lock()
        self._settings_lock = threading.Lock()
        self._persister_lock = threading.Lock()
        self._notification_handlers = {}  # See `add_notification_handler`
        self.cleanups = []  # functions to run on the device when it is closed

        if not self.path:
            self.path = self.low_level.find_paired_node(receiver.path, number, 1) if receiver else None
        if not self.handle:
            try:
                self.handle = self.low_level.open_path(self.path) if self.path else None
            except Exception:  # maybe the device wasn't set up
                try:
                    time.sleep(1)
                    self.handle = self.low_level.open_path(self.path) if self.path else None
                except Exception:  # give up
                    self.handle = None  # should this give up completely?

        if receiver:
            if not self.wpid:
                raise exceptions.NoSuchDevice(
                    number=number, receiver=receiver, error="no wpid for device connected to receiver"
                )
            self.descriptor = descriptors.get_wpid(self.wpid)
            if self.descriptor is None:
                codename = self.receiver.device_codename(self.number)  # Last chance to get a descriptor, may fail
                if codename:
                    self._codename = codename
                    self.descriptor = descriptors.get_codename(self._codename)
        else:
            self.descriptor = (
                descriptors.get_btid(self.product_id) if self.bluetooth else descriptors.get_usbid(self.product_id)
            )
            if self.number is None:  # for direct-connected devices get 'number' from descriptor protocol else use 0xFF
                if self.descriptor and self.descriptor.protocol and self.descriptor.protocol < 2.0:
                    number = 0x00
                else:
                    number = 0xFF
                self.number = number
            self.ping()  # determine whether a direct-connected device is online

        if self.descriptor:
            self._name = self.descriptor.name
            if self._codename is None:
                self._codename = self.descriptor.codename
            if self._kind is None:
                self._kind = self.descriptor.kind
            self._protocol = self.descriptor.protocol if self.descriptor.protocol else None
            self.registers = self.descriptor.registers if self.descriptor.registers else []

        if self._protocol is not None:
            self.features = None if self._protocol < 2.0 else hidpp20.FeaturesArray(self)
        else:
            self.features = hidpp20.FeaturesArray(self)  # may be a 2.0 device; if not, it will fix itself later

        Device.instances.append(self)

    def find(self, id):  # find a device by serial number or unit ID
        assert id, "need serial number or unit ID to find a device"
        for device in Device.instances:
            if device.online and (device.unitId == id or device.serial == id):
                return device

    @property
    def protocol(self):
        if not self._protocol:
            self.ping()
        return self._protocol or 0

    @property
    def codename(self):
        if not self._codename:
            if self.online and self.protocol >= 2.0:
                self._codename = _hidpp20.get_friendly_name(self)
                if not self._codename:
                    self._codename = self.name.split(" ", 1)[0] if self.name else None
            if not self._codename and self.receiver:
                codename = self.receiver.device_codename(self.number)
                if codename:
                    self._codename = codename
                elif self.protocol < 2.0:
                    self._codename = "? (%s)" % (self.wpid or self.product_id)
        return self._codename or "?? (%s)" % (self.wpid or self.product_id)

    @property
    def name(self):
        if not self._name:
            if self.online and self.protocol >= 2.0:
                self._name = _hidpp20.get_name(self)
        return self._name or self._codename or "Unknown device %s" % (self.wpid or self.product_id)

    def get_ids(self):
        ids = _hidpp20.get_ids(self)
        if ids:
            self._unitId, self._modelId, self._tid_map = ids
            if logger.isEnabledFor(logging.INFO) and self._serial and self._serial != self._unitId:
                logger.info("%s: unitId %s does not match serial %s", self, self._unitId, self._serial)

    @property
    def unitId(self):
        if not self._unitId and self.online and self.protocol >= 2.0:
            self.get_ids()
        return self._unitId

    @property
    def modelId(self):
        if not self._modelId and self.online and self.protocol >= 2.0:
            self.get_ids()
        return self._modelId

    @property
    def tid_map(self):
        if not self._tid_map and self.online and self.protocol >= 2.0:
            self.get_ids()
        return self._tid_map

    @property
    def kind(self):
        if not self._kind and self.online and self.protocol >= 2.0:
            self._kind = _hidpp20.get_kind(self)
        return self._kind or "?"

    @property
    def firmware(self) -> tuple[common.FirmwareInfo]:
        if self._firmware is None and self.online:
            if self.protocol >= 2.0:
                self._firmware = _hidpp20.get_firmware(self)
            else:
                self._firmware = _hidpp10.get_firmware(self)
        return self._firmware or ()

    @property
    def serial(self):
        return self._serial or ""

    @property
    def id(self):
        return self.unitId or self.serial

    @property
    def power_switch_location(self):
        return self._power_switch

    @property
    def polling_rate(self):
        if self.online and self.protocol >= 2.0:
            rate = _hidpp20.get_polling_rate(self)
            self._polling_rate = rate if rate else self._polling_rate
        return self._polling_rate

    @property
    def led_effects(self):
        if not self._led_effects and self.online and self.protocol >= 2.0:
            if SupportedFeature.COLOR_LED_EFFECTS in self.features:
                self._led_effects = hidpp20.LEDEffectsInfo(self)
            elif SupportedFeature.RGB_EFFECTS in self.features:
                self._led_effects = hidpp20.RGBEffectsInfo(self)
        return self._led_effects

    @property
    def keys(self):
        if not self._keys:
            if self.online and self.protocol >= 2.0:
                self._keys = _hidpp20.get_keys(self) or ()
        return self._keys

    @property
    def remap_keys(self):
        if self._remap_keys is None:
            if self.online and self.protocol >= 2.0:
                self._remap_keys = _hidpp20.get_remap_keys(self) or ()
        return self._remap_keys

    @property
    def gestures(self):
        if self._gestures is None:
            with self._gestures_lock:
                if self._gestures is None:
                    if self.online and self.protocol >= 2.0:
                        self._gestures = _hidpp20.get_gestures(self) or ()
        return self._gestures

    @property
    def backlight(self):
        if self._backlight is None:
            if self.online and self.protocol >= 2.0:
                self._backlight = _hidpp20.get_backlight(self)
        return self._backlight

    @property
    def profiles(self):
        if self._profiles is None:
            if self.online and self.protocol >= 2.0:
                self._profiles = _hidpp20.get_profiles(self)
        return self._profiles

    def set_configuration(self, configuration_, no_reply=False):
        if self.online and self.protocol >= 2.0:
            _hidpp20.config_change(self, configuration_, no_reply=no_reply)

    def reset(self, no_reply=False):
        self.set_configuration(0, no_reply)

    @property
    def persister(self):
        if not self._persister:
            with self._persister_lock:
                if not self._persister:
                    self._persister = configuration.persister(self)
        return self._persister

    @property
    def settings(self):
        if not self._settings:
            with self._settings_lock:
                if not self._settings:
                    settings = []
                    if self.persister and self.descriptor and self.descriptor.settings:
                        for sclass in self.descriptor.settings:
                            try:
                                setting = sclass.build(self)
                            except Exception as e:  # Do nothing if the device is offline
                                setting = None
                                if self.online:
                                    raise e
                            if setting is not None:
                                settings.append(setting)
                    self._settings = settings
        if not self._feature_settings_checked:
            with self._settings_lock:
                if not self._feature_settings_checked:
                    self._feature_settings_checked = settings_templates.check_feature_settings(self, self._settings)
        return self._settings

    def battery(self):  # None  or  level, next, status, voltage
        if self.protocol < 2.0:
            return _hidpp10.get_battery(self)
        else:
            battery_feature = self.persister.get("_battery", None) if self.persister else None
            if battery_feature != 0:
                result = _hidpp20.get_battery(self, battery_feature)
                try:
                    feature, battery = result
                    if self.persister and battery_feature is None:
                        self.persister["_battery"] = feature.value
                    return battery
                except Exception:
                    if self.persister and battery_feature is None:
                        self.persister["_battery"] = result

    def set_battery_info(self, info):
        """Update battery information for device, calling changed callback if necessary"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: battery %s, %s", self, info.level, info.status)
        if info.level is None and self.battery_info:  # use previous level if missing from new information
            info.level = self.battery_info.level

        changed = self.battery_info != info
        self.battery_info, old_info = info, self.battery_info
        if old_info is None:
            old_info = Battery(None, None, None, None)

        alert, reason = Alert.NONE, None
        if not info.ok():
            logger.warning("%s: battery %d%%, ALERT %s", self, info.level, info.status)
            if old_info.status != info.status:
                alert = Alert.NOTIFICATION | Alert.ATTENTION
            reason = info.to_str()

        if changed or reason:
            # update the leds on the device, if any
            _hidpp10.set_3leds(self, info.level, charging=info.charging(), warning=bool(alert))
            self.changed(active=True, alert=alert, reason=reason)

    # Retrieve and regularize battery status
    def read_battery(self):
        if self.online:
            battery = self.battery()
            self.set_battery_info(battery if battery is not None else Battery(None, None, None, None))

    def changed(self, active=None, alert=Alert.NONE, reason=None, push=False):
        """The status of the device had changed, so invoke the status callback.
        Also push notifications and settings to the device when necessary."""
        if active is not None:
            self.online = active
            was_active, self._active = self._active, active
            if active:
                # Push settings for new devices when devices request software reconfiguration
                # and when devices become active if they don't have wireless device status feature,
                if (
                    was_active is None
                    or not was_active
                    or push
                    and (not self.features or SupportedFeature.WIRELESS_DEVICE_STATUS not in self.features)
                ):
                    if logger.isEnabledFor(logging.INFO):
                        logger.info("%s pushing device settings %s", self, self.settings)
                    settings.apply_all_settings(self)
                if not was_active:
                    if self.protocol < 2.0:  # Make sure to set notification flags on the device
                        self.notification_flags = self.enable_connection_notifications()
                    else:
                        self.set_configuration(0x11)  # signal end of configuration
                    self.read_battery()  # battery information may have changed so try to read it now
            elif was_active and self.receiver:  # need to set configuration pending flag in receiver
                hidpp10.set_configuration_pending_flags(self.receiver, 0xFF)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("device %d changed: active=%s %s", self.number, self._active, self.battery_info)
        if self.status_callback is not None:
            self.status_callback(self, alert, reason)

    def enable_connection_notifications(self, enable=True):
        """Enable or disable device (dis)connection notifications on this
        receiver."""
        if not bool(self.receiver) or self.protocol >= 2.0:
            return False

        if enable:
            set_flag_bits = (
                NotificationFlag.BATTERY_STATUS | NotificationFlag.UI | NotificationFlag.CONFIGURATION_COMPLETE
            ).value
        else:
            set_flag_bits = 0
        ok = _hidpp10.set_notification_flags(self, set_flag_bits)
        if not ok:
            logger.warning("%s: failed to %s device notifications", self, "enable" if enable else "disable")

        flag_bits = _hidpp10.get_notification_flags(self)
        if logger.isEnabledFor(logging.INFO):
            if flag_bits is None:
                flag_names = None
            else:
                flag_names = hidpp10_constants.NotificationFlag.flag_names(flag_bits)
            is_enabled = "enabled" if enable else "disabled"
            logger.info(f"{self}: device notifications {is_enabled} {flag_names}")
        return flag_bits if ok else None

    def add_notification_handler(self, id: str, fn):
        """Adds the notification handling callback `fn` to this device under name `id`.
        If a callback has already been registered under this name, it's replaced with
        the argument.
        The callback will be invoked whenever the device emits an event message, and
        the resulting notification hasn't been handled by another handler on this device
        (order is not guaranteed, so handlers should not overlap in functionality).
        The callback should have type `(PairedDevice, Notification) -> Optional[bool]`.
        It should return `None` if it hasn't handled the notification, return `True`
        if it did so successfully and return `False` if an error should be reported
        (malformed notification, etc).
        """
        self._notification_handlers[id] = fn

    def remove_notification_handler(self, id: str):
        """Unregisters the notification handler under name `id`."""

        if id not in self._notification_handlers and logger.isEnabledFor(logging.INFO):
            logger.info(f"Tried to remove nonexistent notification handler {id} from device {self}.")
        else:
            del self._notification_handlers[id]

    def handle_notification(self, n) -> Optional[bool]:
        for h in self._notification_handlers.values():
            ret = h(self, n)
            if ret is not None:
                return ret
        return None

    def request(self, request_id, *params, no_reply=False):
        if self:
            long = self.hidpp_long is True or (
                self.hidpp_long is None and (self.bluetooth or self._protocol is not None and self._protocol >= 2.0)
            )
            return self.low_level.request(
                self.handle or self.receiver.handle,
                self.number,
                request_id,
                *params,
                no_reply=no_reply,
                long_message=long,
                protocol=self.protocol,
            )

    def feature_request(self, feature, function=0x00, *params, no_reply=False):
        if self.protocol >= 2.0:
            return hidpp20.feature_request(self, feature, function, *params, no_reply=no_reply)

    def ping(self):
        """Checks if the device is online, returns True of False"""
        long = self.hidpp_long is True or (
            self.hidpp_long is None and (self.bluetooth or self._protocol is not None and self._protocol >= 2.0)
        )
        handle = self.handle or self.receiver.handle
        protocol = self.low_level.ping(handle, self.number, long_message=long)
        self.online = protocol is not None
        if protocol:
            self._protocol = protocol
        return self.online

    def notify_devices(self):  # no need to notify, as there are none
        pass

    def close(self):
        handle, self.handle = self.handle, None
        if self in Device.instances:
            Device.instances.remove(self)
        if hasattr(self, "cleanups"):
            for cleanup in self.cleanups:
                cleanup(self)
        return handle and self.low_level.close(handle)

    def __index__(self):
        return self.number

    __int__ = __index__

    def __eq__(self, other):
        return other is not None and self._kind == other._kind and self.wpid == other.wpid

    def __ne__(self, other):
        return other is None or self.kind != other.kind or self.wpid != other.wpid

    def __hash__(self):
        return self.wpid.__hash__()

    def __bool__(self):
        return self.wpid is not None and self.number in self.receiver if self.receiver else self.handle is not None

    __nonzero__ = __bool__

    def status_string(self):
        return self.battery_info.to_str() if self.battery_info is not None else ""

    def __str__(self):
        try:
            name = self._name or self._codename or "?"
        except exceptions.NoSuchDevice:
            name = "name not available"
        return f"<Device({int(self.number)},{self.wpid or self.product_id},{name},{self.serial})>"

    __repr__ = __str__

    def __del__(self):
        self.close()
