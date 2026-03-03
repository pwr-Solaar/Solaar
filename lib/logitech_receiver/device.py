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
import struct
import threading
import time
import typing

from typing import Callable
from typing import Optional
from typing import Protocol

from solaar import configuration

from . import base
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


def _read_usb_product_string(hidraw_path):
    """Read the USB product string from sysfs for a hidraw device path."""
    import pathlib

    try:
        # /sys/class/hidraw/hidrawN/device/../../product → USB device product string
        hidraw_name = pathlib.Path(hidraw_path).name
        product_path = pathlib.Path("/sys/class/hidraw") / hidraw_name / "device" / ".." / ".." / "product"
        product = product_path.read_text().strip()
        return product if product else None
    except (OSError, ValueError):
        return None


class CenturionReceiver:
    """A lightweight receiver-like container for Centurion (PRO X 2 LIGHTSPEED) dongles.

    Provides the Receiver interface to the UI so the dongle appears as a parent
    with the headset as an indented child device. NOT a subclass of Receiver —
    Receiver's __init__ does HID++ 1.0 register reads and pairing setup that
    don't apply to Centurion.

    All centurion communication (bridge, features, settings, battery) lives in
    the child Device; this class is just a UI container + handle owner.
    """

    read_register: Callable = hidpp10.read_register
    write_register: Callable = hidpp10.write_register
    number = 0xFF
    kind = None
    isDevice = False
    may_unpair = False
    re_pairs = False
    max_devices = 1

    def __init__(self, low_level, handle, device_info, setting_callback=None):
        assert handle
        self.low_level = low_level
        self.handle = handle
        self.path = device_info.path
        self.product_id = device_info.product_id
        self.setting_callback = setting_callback
        self.status_callback = None
        self.notification_flags = None
        self._devices = {}
        self._firmware = None
        self._dongle_features = None  # independently probed dongle features
        self.cleanups = []

        # Receiver identity
        self.serial = None
        self._usb_name = getattr(device_info, "product", None)
        if not self._usb_name and self.path:
            self._usb_name = _read_usb_product_string(self.path)
        self.name = "Centurion Receiver"

        # Dummy pairing object — lock_open stays False
        from .receiver import Pairing

        self.pairing = Pairing()

        # Discover dongle features independently
        self._discover_dongle_features()

        # Read serial from dongle's CENTURION_DEVICE_INFO if available
        if self.serial is None:
            try:
                s = _hidpp20.get_serial_centurion(self)
                if s and s.strip() and s.strip().isprintable():
                    self.serial = s.strip()
            except Exception:
                pass

    def enable_connection_notifications(self, enable=True):
        return False

    def remaining_pairings(self, cache=True):
        return None

    def device_codename(self, n):
        return self._usb_name

    def request(self, request_id, *params, no_reply=False):
        """Send an HID++ request directly to the dongle (not through bridge)."""
        if self.handle:
            return self.low_level.request(
                self.handle, 0xFF, request_id, *params, no_reply=no_reply, long_message=True, protocol=2.0
            )

    def feature_request(self, feature, function=0x00, *params, no_reply=False):
        """Send a feature request to the dongle using discovered feature indices."""
        if self._dongle_features is None:
            self._discover_dongle_features()
        feature_int = int(feature)
        for _feat, feat_id, index in (self._dongle_features or []):
            if feat_id == feature_int:
                request_id = (index << 8) | (function & 0xFF)
                return self.request(request_id, *params, no_reply=no_reply)
        raise exceptions.FeatureNotSupported(feature)

    def _discover_dongle_features(self):
        """Independently discover features on the dongle hardware."""
        self._dongle_features = []
        try:
            # Query ROOT for FEATURE_SET index
            response = self.request(0x0000, 0x00, 0x01)
            if response is None or response[0] == 0:
                return
            fs_index = response[0]
            # Get feature count
            count_resp = self.request(fs_index << 8)
            if count_resp is None:
                return
            feature_count = count_resp[0]
            # Enumerate features via CenturionFeatureSet (func 1 = 0x10, per-index query)
            for idx in range(feature_count):
                resp = self.request((fs_index << 8) | 0x10, idx)
                if resp is None or len(resp) < 3:
                    continue
                feat_id = struct.unpack("!H", resp[1:3])[0]
                try:
                    feature = SupportedFeature(feat_id)
                except ValueError:
                    feature = f"unknown:{feat_id:04X}"
                self._dongle_features.append((feature, feat_id, idx))
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Centurion dongle features: %s", self._dongle_features)
        except Exception:
            logger.debug("Centurion dongle feature discovery failed", exc_info=True)

    @property
    def dongle_features(self):
        """Return list of (feature, feat_id, index) tuples for dongle features."""
        if self._dongle_features is None:
            self._discover_dongle_features()
        return self._dongle_features

    def count(self):
        return len([d for d in self._devices.values() if d is not None])

    @property
    def firmware(self):
        if self._firmware is None and self.handle:
            self._firmware = _hidpp20.get_firmware_centurion(self)
        return self._firmware or ()

    def notify_devices(self):
        """Create child Device for the headset and trigger its initialization."""
        # Signal receiver to UI first — tray/window need the receiver entry
        # before a child device can be added under it.
        self.changed()

        # Create child Device with receiver=self, number=1
        pairing_info = {
            "wpid": self.product_id,
            "kind": None,
            "serial": None,
            "polling": None,
            "power_switch": None,
        }
        dev = Device(
            self.low_level,
            self,
            1,
            None,
            pairing_info=pairing_info,
            setting_callback=self.setting_callback,
        )
        # Set centurion attributes on the child
        dev.centurion = True
        dev.product_id = self.product_id
        dev.hidpp_long = True
        dev._centurion_usb_name = self._usb_name

        self._devices[1] = dev
        configuration.attach_to(dev)
        dev.status_callback = self.status_callback

        # Ping to determine online status
        if dev.ping():
            dev.changed(active=True)
        if self.status_callback is not None:
            self.status_callback(dev)

    def changed(self, alert=Alert.NOTIFICATION, reason=None):
        if self.status_callback is not None:
            self.status_callback(self, alert=alert, reason=reason)

    def status_string(self):
        count = self.count()
        if count == 0:
            return "No devices."
        return f"{count} device connected."

    def close(self):
        handle, self.handle = self.handle, None
        for _n, d in self._devices.items():
            if d:
                d.close()
        self._devices.clear()
        for cleanup in self.cleanups:
            cleanup(self)
        return handle and self.low_level.close(handle)

    def __del__(self):
        self.close()

    def __iter__(self):
        for dev in self._devices.values():
            if dev is not None:
                yield dev

    def __getitem__(self, key):
        dev = self._devices.get(key)
        if dev is not None:
            return dev
        raise IndexError(key)

    def __len__(self):
        return len([d for d in self._devices.values() if d is not None])

    def __contains__(self, dev):
        if isinstance(dev, int):
            return self._devices.get(dev) is not None
        return self.__contains__(dev.number)

    def __bool__(self):
        return self.handle is not None

    __nonzero__ = __bool__

    def __eq__(self, other):
        return other is not None and self.kind == other.kind and self.path == other.path

    def __ne__(self, other):
        return other is None or self.kind != other.kind or self.path != other.path

    def __hash__(self):
        return self.path.__hash__()

    def __str__(self):
        return "<%s(%s,%s%s)>" % (
            self.name.replace(" ", "") if self.name else "CenturionReceiver",
            self.path,
            "" if isinstance(self.handle, int) else "T",
            self.handle,
        )

    __repr__ = __str__


def create_centurion_receiver(low_level: LowLevelInterface, device_info, setting_callback=None):
    """Opens a Centurion dongle and wraps it as a receiver-like container.

    Creates a CenturionReceiver, discovers its features, then checks if
    CentPPBridge (0x0003) is among them. If not, this is a direct-connected
    device (wired headset) — close and return None so the caller can fall
    back to create_device().

    :returns: A CenturionReceiver, or None.
    """
    try:
        handle = low_level.open_path(device_info.path)
        if handle:
            base._centurion_handles.add(int(handle))
            cr = CenturionReceiver(low_level, handle, device_info, setting_callback)
            # Check if any discovered feature is CentPPBridge (0x0003)
            has_bridge = any(feat_id == 0x0003 for _, feat_id, _ in (cr.dongle_features or []))
            if not has_bridge:
                logger.info("Centurion device %s has no bridge, treating as direct device", device_info.path)
                base._centurion_handles.discard(int(handle))
                cr.handle = None  # prevent __del__ from double-closing
                low_level.close(handle)
                return None
            return cr
    except OSError as e:
        logger.exception("open %s", device_info)
        if e.errno == errno.EACCES:
            raise e
    except Exception as e:
        logger.exception("open %s", device_info)
        raise e


def create_device(low_level: LowLevelInterface, device_info, setting_callback=None):
    """Opens a Logitech Device found attached to the machine, by Linux device path.
    :returns: An open file handle for the found receiver, or None.
    """
    try:
        handle = low_level.open_path(device_info.path)
        if handle:
            if getattr(device_info, "centurion", False):
                base._centurion_handles.add(int(handle))
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
            raise e
    except Exception as e:
        logger.exception("open %s", device_info)
        raise e


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
        self.centurion = device_info.centurion if device_info else False
        self._centurion_usb_name = None
        if self.centurion:
            self.hidpp_long = True  # Centurion devices always use long HID++ messages
            # Read USB product string for device name — avoids slow bridge probe via CENTURION_DEVICE_NAME.
            # device_info.product is often None (udev reads USB interface attrs, not device attrs),
            # so fall back to reading from sysfs.
            self._centurion_usb_name = getattr(device_info, "product", None) if device_info else None
            if not self._centurion_usb_name and self.path:
                self._centurion_usb_name = _read_usb_product_string(self.path)
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
        self._led_effects = self._firmware = self._keys = self._remap_keys = self._gestures = self._force_buttons = None
        self._profiles = self._backlight = self._settings = None
        self.registers = []
        self.notification_flags = None
        self.battery_info = None
        self.link_encrypted = None
        self._active = None  # lags self.online - is used to help determine when to setup devices
        self.present = True  # used for devices that are integral with their receiver but that separately be disconnected

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
            # for direct-connected devices get 'number' from descriptor protocol else use 0xFF
            self.number = 0x00 if self.descriptor and self.descriptor.protocol and self.descriptor.protocol < 2.0 else 0xFF
            try:  # determine whether a direct-connected device is online
                self.ping()
            except exceptions.NoSuchDevice as e:
                if self.number == 0xFF:  # guessed wrong number?
                    self.number = 0x00
                    self.ping()
                else:
                    raise e

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

    def find(self, id):  # find a device by serial number or unit ID or name or codename
        assert id, "need id to find a device"
        for device in Device.instances:
            if device.online and (device.unitId == id or device.serial == id or device.name == id or device.codename == id):
                return device

    @property
    def protocol(self):
        if not self._protocol:
            try:
                self.ping()
            except exceptions.NoSuchDevice:
                logger.warning("device %s inaccessible - no protocol set", self)
        return self._protocol or 0

    @property
    def codename(self):
        if not self._codename:
            if self.online and self.protocol >= 2.0:
                if not self.centurion:
                    self._codename = _hidpp20.get_friendly_name(self)
                if not self._codename:
                    # Centurion names like "PRO X 2 LIGHTSPEED" don't have a meaningful first-word codename,
                    # and there's no friendly name feature — use the full name
                    self._codename = self.name if self.centurion else (self.name.split(" ", 1)[0] if self.name else None)
            if not self._codename and self.receiver:
                codename = self.receiver.device_codename(self.number)
                if codename:
                    self._codename = codename
                elif self.protocol < 2.0:
                    self._codename = "? (%s)" % (self.wpid or self.product_id)
        return self._codename or f"?? ({self.wpid or self.product_id})"

    @property
    def name(self):
        if not self._name:
            if self.online and self.centurion:
                # Try protocol probe first (consistent with other devices), fall back to USB product string
                self._name = _hidpp20.get_name_centurion(self) or getattr(self, "_centurion_usb_name", None)
                if not self._name:
                    self._name = f"Unknown device {self.wpid or self.product_id}"
            elif self.online and self.protocol >= 2.0:
                self._name = _hidpp20.get_name(self)
        return self._name or self._codename or f"Unknown device {self.wpid or self.product_id}"

    def get_ids(self):
        if self.centurion:
            self._get_ids_centurion()
            return
        ids = _hidpp20.get_ids(self)
        if ids:
            self._unitId, self._modelId, self._tid_map = ids
            if logger.isEnabledFor(logging.INFO) and self._serial and self._serial != self._unitId:
                logger.info("%s: unitId %s does not match serial %s", self, self._unitId, self._serial)

    def _get_ids_centurion(self):
        if getattr(self, "_centurion_ids_done", False):
            return
        self._centurion_ids_done = True
        serial = _hidpp20.get_serial_centurion(self)
        if not serial or not serial.strip() or not serial.strip().isprintable():
            serial = _hidpp20.get_serial_centurion_sub(self)
        if serial and serial.strip() and serial.strip().isprintable():
            self._serial = serial.strip()
            self._unitId = self._serial
        hw_info = _hidpp20.get_hardware_info_centurion(self)
        if hw_info:
            model_id, hw_revision, product_id = hw_info
            self._modelId = f"{product_id:04X}"
            self._tid_map = {"usbid": f"{product_id:04X}"}

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
            if self.centurion:
                self._kind = self._infer_kind_centurion()
            else:
                self._kind = _hidpp20.get_kind(self)
        return self._kind or "?"

    def _infer_kind_centurion(self):
        """Infer device kind from Centurion features (sub-device or top-level)."""
        # Check sub-device features (wireless via bridge)
        for feature in getattr(self, "_centurion_sub_features", ()):
            if isinstance(feature, int) and 0x0600 <= feature <= 0x06FF:
                return hidpp10_constants.DEVICE_KIND.headset
        # Check top-level features (direct USB connection, no bridge)
        if self.features:
            for feature, _index in self.features.enumerate():
                feat_int = int(feature) if isinstance(feature, int) else 0
                if 0x0600 <= feat_int <= 0x06FF:
                    return hidpp10_constants.DEVICE_KIND.headset
        return None

    @property
    def firmware(self) -> tuple[common.FirmwareInfo]:
        if self._firmware is None and self.online:
            if self.centurion:
                self._firmware = _hidpp20.get_firmware_centurion_sub(self) or _hidpp20.get_firmware_centurion(self)
            elif self.protocol >= 2.0:
                self._firmware = _hidpp20.get_firmware(self)
            else:
                self._firmware = _hidpp10.get_firmware(self)
        return self._firmware or ()

    @property
    def serial(self):
        if not self._serial and self.online and self.centurion:
            self.get_ids()
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

    def force_buttons(self):
        if self._force_buttons is None:
            if self.online and self.protocol >= 2.0:
                self._force_buttons = _hidpp20.get_force_buttons(self) or ()
        return self._force_buttons

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
                    if self.persister and battery_feature is None and result is not None and result != 0:
                        self.persister["_battery"] = result.value

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
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("device %d changing: active=%s %s present=%s", self.number, active, self._active, self.present)
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
            set_flag_bits = NotificationFlag.BATTERY_STATUS | NotificationFlag.UI | NotificationFlag.CONFIGURATION_COMPLETE
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
            # Centurion child: CPL framing strips devnumber and responses always
            # have devnumber=0xFF, so we must send 0xFF to match responses.
            devnumber = 0xFF if (self.centurion and self.receiver and not self.handle) else self.number
            return self.low_level.request(
                self.handle or (self.receiver.handle if self.receiver else None),
                devnumber,
                request_id,
                *params,
                no_reply=no_reply,
                long_message=long,
                protocol=self.protocol,
            )

    def feature_request(self, feature, function=0x00, *params, no_reply=False):
        if self.protocol >= 2.0:
            if self.centurion:
                # Ensure sub-device features are discovered before routing decision
                if self.features is not None:
                    self.features._check()
                if feature in getattr(self, "_centurion_sub_features", ()):
                    sub_idx = self.features.get(feature)
                    if sub_idx is not None:
                        return self.centurion_bridge_request(sub_idx, function, *params, no_reply=no_reply)
            return hidpp20.feature_request(self, feature, function, *params, no_reply=no_reply)

    def centurion_bridge_request(self, sub_feat_idx, sub_function=0x00, *params, no_reply=False):
        """Send a request to a Centurion sub-device via CentPPBridge.

        Builds the 4-layer nested message:
        Layer 1: [0x51]
        Layer 2: [cpl_length, flags=0x00]
        Layer 3: [bridge_idx, sendFragment_func|swid, bridge_hdr...]
        Layer 4: [sub_cpl=0x00, sub_feat_idx, sub_func|swid, params...]

        Returns the sub-device response data (after bridge header), or None.
        """
        if not getattr(self, "centurion", False):
            raise ValueError("centurion_bridge_request called on non-Centurion device")
        bridge_idx = getattr(self, "_centurion_bridge_index", None)
        if bridge_idx is None:
            raise ValueError("CentPPBridge index not discovered yet")
        handle = self.handle or (self.receiver.handle if self.receiver else None)
        if not handle:
            return None

        sw_id = base._get_next_sw_id()

        # Build sub-device message: [sub_cpl=0x00, sub_feat_idx, sub_func|swid, params...]
        # sub_function is in standard HID++ format: func_number << 4 (e.g. 0x10 for function 1)
        sub_params = b"".join(struct.pack("B", p) if isinstance(p, int) else p for p in params) if params else b""
        sub_msg = struct.pack("BBB", 0x00, sub_feat_idx, (sub_function & 0xF0) | sw_id) + sub_params

        # Build bridge header: [device_id<<4 | len_hi, len_lo]
        # device_id=0 for the headset, len is the sub-message length
        sub_len = len(sub_msg)
        bridge_hdr = struct.pack("BB", (0x00 << 4) | ((sub_len >> 8) & 0x0F), sub_len & 0xFF)

        # Build Layer 3: [bridge_idx, sendFragment_func(1)<<4|swid, bridge_hdr, sub_msg]
        layer3 = struct.pack("BB", bridge_idx, (0x01 << 4) | sw_id) + bridge_hdr + sub_msg

        with base.acquire_timeout(base.handle_lock(handle), handle, base.DEFAULT_TIMEOUT):
            base.write_centurion_cpl(handle, layer3)

            if no_reply:
                return None

            # Read ACK response (immediate echo of bridge_idx + func|swid)
            timeout = base.DEFAULT_TIMEOUT  # same timeout as standard device requests
            request_started = time.time()
            ack_received = False
            while time.time() - request_started < timeout:
                reply = base._read(handle, timeout)
                if not reply:
                    continue
                _report_id, _devnumber, reply_data = reply
                # ACK: short response echoing feat_idx and func|swid
                if len(reply_data) >= 2 and reply_data[0] == bridge_idx:
                    func_sw = reply_data[1]
                    if (func_sw >> 4) == 0x01 and (func_sw & 0x0F) == sw_id:
                        ack_received = True
                        break
                    if (func_sw >> 4) == 0x01 and (func_sw & 0x0F) == 0:
                        # MessageEvent arrived before ACK — validate it's for our request
                        if self._is_bridge_response_for(reply_data, sub_feat_idx):
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug("bridge idx=%d fn=0x%02X -> OK", sub_feat_idx, sub_function)
                            return self._parse_bridge_response(reply_data)
                        # Unsolicited notification, skip it
            if not ack_received:
                logger.warning("centurion_bridge_request: no ACK received")
                return None

            # Read MessageEvent response (bridge function 1 with SW ID 0 = event)
            while time.time() - request_started < timeout:
                reply = base._read(handle, timeout)
                if not reply:
                    continue
                _report_id, _devnumber, reply_data = reply
                if len(reply_data) >= 2 and reply_data[0] == bridge_idx:
                    func_sw = reply_data[1]
                    if (func_sw >> 4) == 0x01 and (func_sw & 0x0F) == 0:
                        if self._is_bridge_response_for(reply_data, sub_feat_idx):
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug("bridge idx=%d fn=0x%02X -> OK", sub_feat_idx, sub_function)
                            return self._parse_bridge_response(reply_data)
                        # Unsolicited notification for a different feature, skip it
            logger.warning("centurion_bridge_request: no MessageEvent received")
            return None

    @staticmethod
    def _is_bridge_response_for(reply_data, expected_sub_feat_idx):
        """Check if a bridge MessageEvent is a response for our specific sub-feature request.

        Accepts both normal responses (sub_feat_idx matches) and error responses
        (sub_feat_idx=0xFF with original feat_idx in next byte).
        Unsolicited notifications (sub_cpl=0xFF) are rejected.
        """
        if len(reply_data) < 6:
            return False
        sub_cpl = reply_data[4]
        sub_feat_idx = reply_data[5]
        # Notifications have sub_cpl=0xFF; our responses have sub_cpl=0x00
        if sub_cpl != 0x00:
            return False
        if sub_feat_idx == expected_sub_feat_idx:
            return True
        # Error response: sub_feat_idx=0xFF, next byte is the original feat_idx that errored
        if sub_feat_idx == 0xFF and len(reply_data) >= 7 and reply_data[6] == expected_sub_feat_idx:
            return True
        return False

    @staticmethod
    def _parse_bridge_response(reply_data):
        """Extract sub-device response from a CentPPBridge MessageEvent.

        reply_data layout (after report_id and devnumber have been stripped):
        [bridge_idx, func_sw, dev_id<<4|len_hi, len_lo, sub_cpl, sub_feat_idx, sub_func_sw, data...]
        Returns the sub-device data starting from sub_feat_idx onward.

        Error responses have sub_feat_idx=0xFF: [... sub_cpl, 0xFF, orig_feat_idx, orig_func_sw, error_code]
        These return None.
        """
        if len(reply_data) < 7:
            return None
        sub_feat_idx = reply_data[5]
        # Error response from sub-device
        if sub_feat_idx == 0xFF:
            error_code = reply_data[8] if len(reply_data) > 8 else 0
            orig_feat_idx = reply_data[6] if len(reply_data) > 6 else 0
            logger.debug("bridge sub-device error: feat_idx=%d error=0x%02X", orig_feat_idx, error_code)
            return None
        return reply_data[7:]  # response data after sub_cpl, sub_feat_idx, sub_func_sw

    def ping(self):
        """Checks if the device is online and present, returns True of False.
        Some devices are integral with their receiver but may not be present even if the receiver responds to ping."""
        if self.centurion and self.receiver and not self.handle:
            # Centurion child: ping the dongle with 0xFF (CPL framing has no device number,
            # and responses always have devnumber=0xFF)
            handle = self.receiver.handle
            try:
                protocol = self.low_level.ping(handle, 0xFF, long_message=True)
            except exceptions.NoReceiver:
                protocol = None
            self.online = protocol is not None and self.present
            if protocol:
                self._protocol = protocol
            return self.online
        long = self.hidpp_long is True or (
            self.hidpp_long is None and (self.bluetooth or self._protocol is not None and self._protocol >= 2.0)
        )
        handle = self.handle or self.receiver.handle
        try:
            protocol = self.low_level.ping(handle, self.number, long_message=long)
        except exceptions.NoReceiver:  # if ping fails, device is offline
            protocol = None
        self.online = protocol is not None and self.present
        if protocol:
            self._protocol = protocol
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("pinged %s: online %s protocol %s present %s", self.number, self.online, protocol, self.present)
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
