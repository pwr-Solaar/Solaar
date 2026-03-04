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

"""Centurion device protocol — receiver class, factory, device info/firmware/battery queries.

CenturionReceiver is a lightweight receiver-like container for Centurion
(PRO X 2 LIGHTSPEED and similar) dongles. Protocol functions query device
info, firmware, serial, name, and battery via Centurion-specific HID++ features.
"""

from __future__ import annotations

import errno
import logging
import struct

from typing import Callable

from solaar import configuration

from . import base
from . import exceptions
from . import hidpp10
from .common import Alert
from .common import Battery
from .common import BatteryStatus
from .common import FirmwareKind
from .common import _read_usb_product_string
from .hidpp20_constants import SupportedFeature

logger = logging.getLogger(__name__)


# --- Centurion protocol functions (standalone, operate on any device-like object) ---


def get_firmware_centurion(device):
    """Reads firmware info from a Centurion device via DeviceInfo (0x0100) function 1."""
    from . import common

    fw = []
    seen = set()  # track response signatures to detect duplicates
    for index in range(0, 8):  # try up to 8 entities
        try:
            report = device.feature_request(SupportedFeature.CENTURION_DEVICE_INFO, 0x10, index)
        except exceptions.FeatureCallError:
            break
        if not report or len(report) < 5:
            break
        # Dedup: parent device returns the same response for every entity index
        sig = bytes(report[: 5 + report[4]])
        if sig in seen:
            break
        seen.add(sig)
        fw_type = report[0]
        version = struct.unpack("!H", report[2:4])[0]
        name_len = report[4]
        name = report[5 : 5 + name_len].decode("ascii", errors="replace").rstrip("\x00") if name_len else ""
        version_str = f"{version >> 8}.{version & 0xFF:02d}"
        kind = FirmwareKind(fw_type) if fw_type <= 3 else FirmwareKind.Other
        fw.append(common.FirmwareInfo(kind, name, version_str, None))
    return tuple(fw) if fw else None


def get_serial_centurion(device):
    """Reads the serial number from a Centurion device via DeviceInfo (0x0100) function 2."""
    try:
        report = device.feature_request(SupportedFeature.CENTURION_DEVICE_INFO, 0x20)
    except exceptions.FeatureCallError:
        return None
    if not report or len(report) < 2:
        return None
    str_len = report[0]
    return report[1 : 1 + str_len].decode("ascii", errors="replace").rstrip("\x00")


def get_hardware_info_centurion(device):
    """Reads hardware info from a Centurion device via DeviceInfo (0x0100) function 0.

    Returns (modelId, hardwareRevision, productId) or None.
    """
    try:
        report = device.feature_request(SupportedFeature.CENTURION_DEVICE_INFO)
    except exceptions.FeatureCallError:
        return None
    if not report or len(report) < 4:
        return None
    model_id = report[0]
    hw_revision = report[1]
    product_id = struct.unpack("!H", report[2:4])[0]
    return model_id, hw_revision, product_id


def _centurion_sub_device_info_request(device, function=0x00, *params):
    """Send a DeviceInfo (0x0100) request to the sub-device via bridge."""
    sub_indices = getattr(device, "_centurion_sub_indices", {})
    sub_idx = sub_indices.get(SupportedFeature.CENTURION_DEVICE_INFO)
    if sub_idx is None:
        return None
    return device.centurion_bridge_request(sub_idx, function, *params)


def get_firmware_centurion_sub(device):
    """Reads firmware info from the Centurion sub-device (headset) via bridge."""
    from . import common

    fw = []
    seen = set()
    for index in range(0, 8):
        report = _centurion_sub_device_info_request(device, 0x10, index)
        if not report or len(report) < 5:
            break
        sig = bytes(report[: 5 + report[4]])
        if sig in seen:
            break
        seen.add(sig)
        fw_type = report[0]
        version = struct.unpack("!H", report[2:4])[0]
        name_len = report[4]
        name = report[5 : 5 + name_len].decode("ascii", errors="replace").rstrip("\x00") if name_len else ""
        version_str = f"{version >> 8}.{version & 0xFF:02d}"
        kind = FirmwareKind(fw_type) if fw_type <= 3 else FirmwareKind.Other
        fw.append(common.FirmwareInfo(kind, name, version_str, None))
    return tuple(fw) if fw else None


def get_serial_centurion_sub(device):
    """Reads the serial number from the Centurion sub-device (headset) via bridge."""
    report = _centurion_sub_device_info_request(device, 0x20)
    if not report or len(report) < 2:
        return None
    str_len = report[0]
    return report[1 : 1 + str_len].decode("ascii", errors="replace").rstrip("\x00")


def get_hardware_info_centurion_sub(device):
    """Reads hardware info from the Centurion sub-device (headset) via bridge.

    Returns (modelId, hardwareRevision, productId) or None.
    """
    report = _centurion_sub_device_info_request(device)
    if not report or len(report) < 4:
        return None
    model_id = report[0]
    hw_revision = report[1]
    product_id = struct.unpack("!H", report[2:4])[0]
    return model_id, hw_revision, product_id


def get_name_centurion(device):
    """Reads a Centurion device's name via DeviceName (0x0101).

    Tries two response formats:
    1. Inline: function 0 returns [name_len, name_bytes...] (like serial)
    2. Chunked: function 0 returns [name_len], function 1 returns [name_bytes...] (like standard DeviceName)
    """
    try:
        reply = device.feature_request(SupportedFeature.CENTURION_DEVICE_NAME)
    except exceptions.FeatureCallError:
        return None
    if not reply:
        return None
    name_length = reply[0]
    if name_length == 0:
        return None
    # If the full name is inline (length + name bytes in one response)
    if len(reply) >= 1 + name_length:
        return reply[1 : 1 + name_length].decode("utf-8", errors="replace").rstrip("\x00")
    # Otherwise, fetch name in chunks via function 1 (like standard DEVICE_NAME)
    name = b""
    while len(name) < name_length:
        try:
            fragment = device.feature_request(SupportedFeature.CENTURION_DEVICE_NAME, 0x10, len(name))
        except exceptions.FeatureCallError:
            break
        if fragment:
            name += fragment[: name_length - len(name)]
        else:
            break
    return name.decode("utf-8", errors="replace").rstrip("\x00") if name else None


def get_battery_centurion(device):
    """Query battery via CENTURION_BATTERY_SOC."""
    try:
        report = device.feature_request(SupportedFeature.CENTURION_BATTERY_SOC)
        if report is not None:
            return decipher_battery_centurion(report)
    except exceptions.FeatureCallError:
        if SupportedFeature.CENTURION_BATTERY_SOC in device.features:
            return SupportedFeature.CENTURION_BATTERY_SOC
        return None


def decipher_battery_centurion(report) -> tuple[SupportedFeature, Battery]:
    """Decipher CENTURION_BATTERY_SOC (0x0104) response.

    Response format (3 bytes):
      Byte 0: Battery Percentage (0-100)
      Byte 1: Battery Percentage (duplicate)
      Byte 2: Charging Status (0=discharging, 1=charging, 2=charging via USB, 3=charge complete)
    """
    if len(report) < 1:
        return SupportedFeature.CENTURION_BATTERY_SOC, Battery(None, None, BatteryStatus.DISCHARGING, None)
    soc = report[0]
    logger.debug("centurion battery SOC raw: %s", report[:8].hex())
    charging_status = report[2] if len(report) >= 3 else 0
    if charging_status in (1, 2):
        status = BatteryStatus.RECHARGING
    elif charging_status == 3:
        status = BatteryStatus.FULL
    else:
        status = BatteryStatus.DISCHARGING
    return SupportedFeature.CENTURION_BATTERY_SOC, Battery(soc, None, status, None)


# --- CenturionReceiver class ---


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
                s = get_serial_centurion(self)
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
        for _feat, feat_id, index in self._dongle_features or []:
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
            self._firmware = get_firmware_centurion(self)
        return self._firmware or ()

    def notify_devices(self):
        """Create child Device for the headset and trigger its initialization."""
        # Import Device locally to avoid circular import (centurion.py ↔ device.py)
        from .device import Device

        # Signal receiver to UI first — tray/window need the receiver entry
        # before a child device can be added under it.
        self.changed(alert=Alert.NONE)

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
        # Pre-set bridge index from dongle features so ping can probe the headset
        for _feat, feat_id, idx in self._dongle_features or []:
            if feat_id == 0x0003:  # CentPPBridge
                dev._centurion_bridge_index = idx
                break

        self._devices[1] = dev
        configuration.attach_to(dev)
        dev.status_callback = self.status_callback

        # Ping to determine online status.
        # Notify UI either way — offline devices show as greyed out (matching receiver behavior).
        online = dev.ping()
        dev.changed(active=online)
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


def create_centurion_receiver(low_level, device_info, setting_callback=None):
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
