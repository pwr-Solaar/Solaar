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

# Logitech Unifying Receiver API.

import threading as _threading

from logging import DEBUG as _DEBUG
from logging import ERROR as _ERROR
from logging import INFO as _INFO
from logging import WARNING as _WARNING
from logging import getLogger
from struct import pack as _pack
from struct import unpack as _unpack
from typing import List

from . import special_keys
from .common import BATTERY_APPROX as _BATTERY_APPROX
from .common import FirmwareInfo as _FirmwareInfo
from .common import KwException as _KwException
from .common import NamedInt as _NamedInt
from .common import NamedInts as _NamedInts
from .common import UnsortedNamedInts as _UnsortedNamedInts
from .common import bytes2int as _bytes2int
from .common import int2bytes as _int2bytes

_log = getLogger(__name__)
del getLogger

#
#
#

# <FeaturesSupported.xml sed '/LD_FID_/{s/.*LD_FID_/\t/;s/"[ \t]*Id="/=/;s/" \/>/,/p}' | sort -t= -k2
# additional features names taken from https://github.com/cvuchener/hidpp and
# https://github.com/Logitech/cpg-docs/tree/master/hidpp20
"""Possible features available on a Logitech device.

A particular device might not support all these features, and may support other
unknown features as well.
"""
FEATURE = _NamedInts(
    ROOT=0x0000,
    FEATURE_SET=0x0001,
    FEATURE_INFO=0x0002,
    # Common
    DEVICE_FW_VERSION=0x0003,
    DEVICE_UNIT_ID=0x0004,
    DEVICE_NAME=0x0005,
    DEVICE_GROUPS=0x0006,
    DEVICE_FRIENDLY_NAME=0x0007,
    KEEP_ALIVE=0x0008,
    RESET=0x0020,  # "Config Change"
    CRYPTO_ID=0x0021,
    TARGET_SOFTWARE=0x0030,
    WIRELESS_SIGNAL_STRENGTH=0x0080,
    DFUCONTROL_LEGACY=0x00C0,
    DFUCONTROL_UNSIGNED=0x00C1,
    DFUCONTROL_SIGNED=0x00C2,
    DFUCONTROL=0x00C3,
    DFU=0x00D0,
    BATTERY_STATUS=0x1000,
    BATTERY_VOLTAGE=0x1001,
    UNIFIED_BATTERY=0x1004,
    CHARGING_CONTROL=0x1010,
    LED_CONTROL=0x1300,
    GENERIC_TEST=0x1800,
    DEVICE_RESET=0x1802,
    OOBSTATE=0x1805,
    CONFIG_DEVICE_PROPS=0x1806,
    CHANGE_HOST=0x1814,
    HOSTS_INFO=0x1815,
    BACKLIGHT=0x1981,
    BACKLIGHT2=0x1982,
    BACKLIGHT3=0x1983,
    ILLUMINATION=0x1990,
    PRESENTER_CONTROL=0x1A00,
    SENSOR_3D=0x1A01,
    REPROG_CONTROLS=0x1B00,
    REPROG_CONTROLS_V2=0x1B01,
    REPROG_CONTROLS_V2_2=0x1B02,  # LogiOptions 2.10.73 features.xml
    REPROG_CONTROLS_V3=0x1B03,
    REPROG_CONTROLS_V4=0x1B04,
    REPORT_HID_USAGE=0x1BC0,
    PERSISTENT_REMAPPABLE_ACTION=0x1C00,
    WIRELESS_DEVICE_STATUS=0x1D4B,
    REMAINING_PAIRING=0x1DF0,
    FIRMWARE_PROPERTIES=0x1F1F,
    ADC_MEASUREMENT=0x1F20,
    # Mouse
    LEFT_RIGHT_SWAP=0x2001,
    SWAP_BUTTON_CANCEL=0x2005,
    POINTER_AXIS_ORIENTATION=0x2006,
    VERTICAL_SCROLLING=0x2100,
    SMART_SHIFT=0x2110,
    SMART_SHIFT_ENHANCED=0x2111,
    HI_RES_SCROLLING=0x2120,
    HIRES_WHEEL=0x2121,
    LOWRES_WHEEL=0x2130,
    THUMB_WHEEL=0x2150,
    MOUSE_POINTER=0x2200,
    ADJUSTABLE_DPI=0x2201,
    POINTER_SPEED=0x2205,
    ANGLE_SNAPPING=0x2230,
    SURFACE_TUNING=0x2240,
    XY_STATS=0x2250,
    WHEEL_STATS=0x2251,
    HYBRID_TRACKING=0x2400,
    # Keyboard
    FN_INVERSION=0x40A0,
    NEW_FN_INVERSION=0x40A2,
    K375S_FN_INVERSION=0x40A3,
    ENCRYPTION=0x4100,
    LOCK_KEY_STATE=0x4220,
    SOLAR_DASHBOARD=0x4301,
    KEYBOARD_LAYOUT=0x4520,
    KEYBOARD_DISABLE_KEYS=0x4521,
    KEYBOARD_DISABLE_BY_USAGE=0x4522,
    DUALPLATFORM=0x4530,
    MULTIPLATFORM=0x4531,
    KEYBOARD_LAYOUT_2=0x4540,
    CROWN=0x4600,
    # Touchpad
    TOUCHPAD_FW_ITEMS=0x6010,
    TOUCHPAD_SW_ITEMS=0x6011,
    TOUCHPAD_WIN8_FW_ITEMS=0x6012,
    TAP_ENABLE=0x6020,
    TAP_ENABLE_EXTENDED=0x6021,
    CURSOR_BALLISTIC=0x6030,
    TOUCHPAD_RESOLUTION=0x6040,
    TOUCHPAD_RAW_XY=0x6100,
    TOUCHMOUSE_RAW_POINTS=0x6110,
    TOUCHMOUSE_6120=0x6120,
    GESTURE=0x6500,
    GESTURE_2=0x6501,
    # Gaming Devices
    GKEY=0x8010,
    MKEYS=0x8020,
    MR=0x8030,
    BRIGHTNESS_CONTROL=0x8040,
    REPORT_RATE=0x8060,
    COLOR_LED_EFFECTS=0x8070,
    RGB_EFFECTS=0x8071,
    PER_KEY_LIGHTING=0x8080,
    PER_KEY_LIGHTING_V2=0x8081,
    MODE_STATUS=0x8090,
    ONBOARD_PROFILES=0x8100,
    MOUSE_BUTTON_SPY=0x8110,
    LATENCY_MONITORING=0x8111,
    GAMING_ATTACHMENTS=0x8120,
    FORCE_FEEDBACK=0x8123,
    # Headsets
    SIDETONE=0x8300,
    EQUALIZER=0x8310,
    HEADSET_OUT=0x8320,
    # Fake features for Solaar internal use
    MOUSE_GESTURE=0xFE00,
)
FEATURE._fallback = lambda x: 'unknown:%04X' % x

FEATURE_FLAG = _NamedInts(internal=0x20, hidden=0x40, obsolete=0x80)

DEVICE_KIND = _NamedInts(
    keyboard=0x00, remote_control=0x01, numpad=0x02, mouse=0x03, touchpad=0x04, trackball=0x05, presenter=0x06, receiver=0x07
)

FIRMWARE_KIND = _NamedInts(Firmware=0x00, Bootloader=0x01, Hardware=0x02, Other=0x03)

BATTERY_OK = lambda status: status not in (BATTERY_STATUS.invalid_battery, BATTERY_STATUS.thermal_error)

BATTERY_STATUS = _NamedInts(
    discharging=0x00,
    recharging=0x01,
    almost_full=0x02,
    full=0x03,
    slow_recharge=0x04,
    invalid_battery=0x05,
    thermal_error=0x06
)

ONBOARD_MODES = _NamedInts(MODE_NO_CHANGE=0x00, MODE_ONBOARD=0x01, MODE_HOST=0x02)

CHARGE_STATUS = _NamedInts(charging=0x00, full=0x01, not_charging=0x02, error=0x07)

CHARGE_LEVEL = _NamedInts(average=50, full=90, critical=5)

CHARGE_TYPE = _NamedInts(standard=0x00, fast=0x01, slow=0x02)

ERROR = _NamedInts(
    unknown=0x01,
    invalid_argument=0x02,
    out_of_range=0x03,
    hardware_error=0x04,
    logitech_internal=0x05,
    invalid_feature_index=0x06,
    invalid_function=0x07,
    busy=0x08,
    unsupported=0x09
)

#
#
#


class FeatureNotSupported(_KwException):
    """Raised when trying to request a feature not supported by the device."""
    pass


class FeatureCallError(_KwException):
    """Raised if the device replied to a feature call with an error."""
    pass


#
#
#


class FeaturesArray(dict):
    def __init__(self, device):
        assert device is not None
        self.supported = True
        self.device = device
        self.inverse = {}
        self.version = {}
        self.count = 0

    def _check(self):
        if self.supported is False or not self.device.online:
            return False
        if self.device.protocol and self.device.protocol < 2.0:
            self.supported = False
            return False
        if self.count > 0:
            return True
        reply = self.device.request(0x0000, _pack('!H', FEATURE.FEATURE_SET))
        if reply is not None:
            fs_index = ord(reply[0:1])
            if fs_index:
                count = self.device.request(fs_index << 8)
                if count is None:
                    _log.warn('FEATURE_SET found, but failed to read features count')
                    return False
                else:
                    self.count = ord(count[:1]) + 1  # ROOT feature not included in count
                    self[FEATURE.ROOT] = 0
                    self[FEATURE.FEATURE_SET] = fs_index
                    return True
            else:
                self.supported = False
        return False

    def get_feature(self, index):
        feature = self.inverse.get(index)
        if feature is not None:
            return feature
        elif self._check():
            response = self.device.feature_request(FEATURE.FEATURE_SET, 0x10, index)
            if response:
                feature = FEATURE[_unpack('!H', response[:2])[0]]
                self[feature] = index
                self.version[feature] = response[3]
                return feature

    def enumerate(self):  # return all features and their index, ordered by index
        if self._check():
            for index in range(self.count):
                feature = self.get_feature(index)
                yield feature, index

    def get_feature_version(self, feature):
        if self[feature]:
            return self.version.get(feature, 0)

    __bool__ = __nonzero__ = _check

    def __getitem__(self, feature):
        index = super().get(feature)
        if index is not None:
            return index
        elif self._check():
            response = self.device.request(0x0000, _pack('!H', feature))
            if response:
                index = response[0]
                self[feature] = index if index else False
                self.version[feature] = response[2]
                return index if index else False

    def __setitem__(self, feature, index):
        if type(super().get(feature)) == int:
            self.inverse.pop(super().get(feature))
        super().__setitem__(feature, index)
        if type(index) == int:
            self.inverse[index] = feature

    def __delitem__(self, feature):
        if type(super().get(feature)) == int:
            self.inverse.pop(super().get(feature))
        super().__delitem__(feature)

    def __contains__(self, feature):  # is a feature present
        index = self.__getitem__(feature)
        return index is not None and index is not False

    def __len__(self):
        return self.count


class ReprogrammableKey:
    """Information about a control present on a device with the `REPROG_CONTROLS` feature.
    Ref: https://drive.google.com/file/d/0BxbRzx7vEV7eU3VfMnRuRXktZ3M/view
    Read-only properties:
    - index {int} -- index in the control ID table
    - key {_NamedInt} -- the name of this control
    - default_task {_NamedInt} -- the native function of this control
    - flags {List[str]} -- capabilities and desired software handling of the control
    """
    def __init__(self, device, index, cid, tid, flags):
        self._device = device
        self.index = index
        self._cid = cid
        self._tid = tid
        self._flags = flags

    @property
    def key(self) -> _NamedInt:
        return special_keys.CONTROL[self._cid]

    @property
    def default_task(self) -> _NamedInt:
        """NOTE: This NamedInt is a bit mixed up, because its value is the Control ID
        while the name is the Control ID's native task. But this makes more sense
        than presenting details of controls vs tasks in the interface. The same
        convention applies to `mapped_to`, `remappable_to`, `remap` in `ReprogrammableKeyV4`."""
        task = str(special_keys.TASK[self._tid])
        return _NamedInt(self._cid, task)

    @property
    def flags(self) -> List[str]:
        return special_keys.KEY_FLAG.flag_names(self._flags)


class ReprogrammableKeyV4(ReprogrammableKey):
    """Information about a control present on a device with the `REPROG_CONTROLS_V4` feature.
    Ref (v2): https://lekensteyn.nl/files/logitech/x1b04_specialkeysmsebuttons.html
    Ref (v4): https://drive.google.com/file/d/10imcbmoxTJ1N510poGdsviEhoFfB_Ua4/view
    Contains all the functionality of `ReprogrammableKey` plus remapping keys and /diverting/ them
    in order to handle keypresses in a custom way.

    Additional read-only properties:
    - pos {int} -- position of this control on the device; 1-16 for FN-keys, otherwise 0
    - group {int} -- the group this control belongs to; other controls with this group in their
    `group_mask` can be remapped to this control
    - group_mask {List[str]} -- this control can be remapped to any control ID in these groups
    - mapped_to {_NamedInt} -- which action this control is mapped to; usually itself
    - remappable_to {List[_NamedInt]} -- list of actions which this control can be remapped to
    - mapping_flags {List[str]} -- mapping flags set on the control
    """
    def __init__(self, device, index, cid, tid, flags, pos, group, gmask):
        ReprogrammableKey.__init__(self, device, index, cid, tid, flags)
        self.pos = pos
        self.group = group
        self._gmask = gmask
        self._mapping_flags = None
        self._mapped_to = None

    @property
    def group_mask(self):
        return special_keys.CID_GROUP_BIT.flag_names(self._gmask)

    @property
    def mapped_to(self) -> _NamedInt:
        if self._mapped_to is None:
            self._getCidReporting()
        self._device.keys._ensure_all_keys_queried()
        task = str(special_keys.TASK[self._device.keys.cid_to_tid[self._mapped_to]])
        return _NamedInt(self._mapped_to, task)

    @property
    def remappable_to(self) -> _NamedInts:
        self._device.keys._ensure_all_keys_queried()
        ret = _UnsortedNamedInts()
        if self.group_mask != []:  # only keys with a non-zero gmask are remappable
            ret[self.default_task] = self.default_task  # it should always be possible to map the key to itself
            for g in self.group_mask:
                g = special_keys.CID_GROUP[str(g)]
                for tgt_cid in self._device.keys.group_cids[g]:
                    tgt_task = str(special_keys.TASK[self._device.keys.cid_to_tid[tgt_cid]])
                    tgt_task = _NamedInt(tgt_cid, tgt_task)
                    if tgt_task != self.default_task:  # don't put itself in twice
                        ret[tgt_task] = tgt_task
        return ret

    @property
    def mapping_flags(self) -> List[str]:
        if self._mapping_flags is None:
            self._getCidReporting()
        return special_keys.MAPPING_FLAG.flag_names(self._mapping_flags)

    def set_diverted(self, value: bool):
        """If set, the control is diverted temporarily and reports presses as HID++ events."""
        flags = {special_keys.MAPPING_FLAG.diverted: value}
        self._setCidReporting(flags=flags)

    def set_persistently_diverted(self, value: bool):
        """If set, the control is diverted permanently and reports presses as HID++ events."""
        flags = {special_keys.MAPPING_FLAG.persistently_diverted: value}
        self._setCidReporting(flags=flags)

    def set_rawXY_reporting(self, value: bool):
        """If set, the mouse temporarily reports all its raw XY events while this control is pressed as HID++ events."""
        flags = {special_keys.MAPPING_FLAG.raw_XY_diverted: value}
        self._setCidReporting(flags=flags)

    def remap(self, to: _NamedInt):
        """Temporarily remaps this control to another action."""
        self._setCidReporting(remap=int(to))

    def _getCidReporting(self):
        try:
            mapped_data = feature_request(self._device, FEATURE.REPROG_CONTROLS_V4, 0x20, *tuple(_pack('!H', self._cid)))
            if mapped_data:
                cid, mapping_flags_1, mapped_to = _unpack('!HBH', mapped_data[:5])
                if cid != self._cid and _log.isEnabledFor(_WARNING):
                    _log.warn(
                        f'REPROG_CONTROLS_V4 endpoint getCidReporting on device {self._device} replied ' +
                        f'with a different control ID ({cid}) than requested ({self._cid}).'
                    )
                self._mapped_to = mapped_to if mapped_to != 0 else self._cid
                if len(mapped_data) > 5:
                    mapping_flags_2, = _unpack('!B', mapped_data[5:6])
                else:
                    mapping_flags_2 = 0
                self._mapping_flags = mapping_flags_1 | (mapping_flags_2 << 8)
            else:
                raise FeatureCallError(msg='No reply from device.')
        except FeatureCallError:  # if the key hasn't ever been configured then the read may fail so only produce a warning
            if _log.isEnabledFor(_WARNING):
                _log.warn(
                    f'Feature Call Error in _getCidReporting on device {self._device} for cid {self._cid} - use defaults'
                )
            # Clear flags and set mapping target to self
            self._mapping_flags = 0
            self._mapped_to = self._cid

    def _setCidReporting(self, flags=None, remap=0):
        """Sends a `setCidReporting` request with the given parameters. Raises an exception if the parameters are invalid.
        Parameters:
        - flags {Dict[_NamedInt,bool]} -- a dictionary of which mapping flags to set/unset
        - remap {int} -- which control ID to remap to; or 0 to keep current mapping
        """
        flags = flags if flags else {}  # See flake8 B006

        # if special_keys.MAPPING_FLAG.raw_XY_diverted in flags and flags[special_keys.MAPPING_FLAG.raw_XY_diverted]:
        # We need diversion to report raw XY, so divert temporarily (since XY reporting is also temporary)
        # flags[special_keys.MAPPING_FLAG.diverted] = True
        # if special_keys.MAPPING_FLAG.diverted in flags and not flags[special_keys.MAPPING_FLAG.diverted]:
        # flags[special_keys.MAPPING_FLAG.raw_XY_diverted] = False

        # The capability required to set a given reporting flag.
        FLAG_TO_CAPABILITY = {
            special_keys.MAPPING_FLAG.diverted: special_keys.KEY_FLAG.divertable,
            special_keys.MAPPING_FLAG.persistently_diverted: special_keys.KEY_FLAG.persistently_divertable,
            special_keys.MAPPING_FLAG.analytics_key_events_reporting: special_keys.KEY_FLAG.analytics_key_events,
            special_keys.MAPPING_FLAG.force_raw_XY_diverted: special_keys.KEY_FLAG.force_raw_XY,
            special_keys.MAPPING_FLAG.raw_XY_diverted: special_keys.KEY_FLAG.raw_XY
        }

        bfield = 0
        for f, v in flags.items():
            if v and FLAG_TO_CAPABILITY[f] not in self.flags:
                raise FeatureNotSupported(
                    msg=f'Tried to set mapping flag "{f}" on control "{self.key}" ' +
                    f'which does not support "{FLAG_TO_CAPABILITY[f]}" on device {self._device}.'
                )
            bfield |= int(f) if v else 0
            bfield |= int(f) << 1  # The 'Xvalid' bit
            if self._mapping_flags:  # update flags if already read
                if v:
                    self._mapping_flags |= int(f)
                else:
                    self._mapping_flags &= ~int(f)

        if remap != 0 and remap not in self.remappable_to:
            raise FeatureNotSupported(
                msg=f'Tried to remap control "{self.key}" to a control ID {remap} which it is not remappable to ' +
                f'on device {self._device}.'
            )
        if remap != 0:  # update mapping if changing (even if not already read)
            self._mapped_to = remap

        pkt = tuple(_pack('!HBH', self._cid, bfield & 0xff, remap))
        # TODO: to fully support version 4 of REPROG_CONTROLS_V4, append `(bfield >> 8) & 0xff` here.
        # But older devices might behave oddly given that byte, so we don't send it.
        ret = feature_request(self._device, FEATURE.REPROG_CONTROLS_V4, 0x30, *pkt)
        if ret is None or _unpack('!BBBBB', ret[:5]) != pkt and _log.isEnabledFor(_DEBUG):
            _log.debug(f"REPROG_CONTROLS_v4 setCidReporting on device {self._device} didn't echo request packet.")


class PersistentRemappableAction():
    def __init__(self, device, index, cid, actionId, remapped, modifierMask, cidStatus):
        self._device = device
        self.index = index
        self._cid = cid
        self.actionId = actionId
        self.remapped = remapped
        self._modifierMask = modifierMask
        self.cidStatus = cidStatus

    @property
    def key(self) -> _NamedInt:
        return special_keys.CONTROL[self._cid]

    @property
    def actionType(self) -> _NamedInt:
        return special_keys.ACTIONID[self._actionId]

    @property
    def action(self):
        if self.actionId == special_keys.ACTIONID.Empty:
            return None
        elif self.actionId == special_keys.ACTIONID.Key:
            return 'Key: ' + str(self.modifiers) + str(self.remapped)
        elif self.actionId == special_keys.ACTIONID.Mouse:
            return 'Mouse Button: ' + str(self.remapped)
        elif self.actionId == special_keys.ACTIONID.Xdisp:
            return 'X Displacement ' + str(self.remapped)
        elif self.actionId == special_keys.ACTIONID.Ydisp:
            return 'Y Displacement ' + str(self.remapped)
        elif self.actionId == special_keys.ACTIONID.Vscroll:
            return 'Vertical Scroll ' + str(self.remapped)
        elif self.actionId == special_keys.ACTIONID.Hscroll:
            return 'Horizontal Scroll: ' + str(self.remapped)
        elif self.actionId == special_keys.ACTIONID.Consumer:
            return 'Consumer: ' + str(self.remapped)
        elif self.actionId == special_keys.ACTIONID.Internal:
            return 'Internal Action ' + str(self.remapped)
        elif self.actionId == special_keys.ACTIONID.Internal:
            return 'Power ' + str(self.remapped)
        else:
            return 'Unknown'

    @property
    def modifiers(self):
        return special_keys.modifiers[self._modifierMask]

    @property
    def data_bytes(self):
        return _int2bytes(self.actionId, 1) + _int2bytes(self.remapped, 2) + _int2bytes(self._modifierMask, 1)

    def remap(self, data_bytes):
        cid = _int2bytes(self._cid, 2)
        if _bytes2int(data_bytes) == special_keys.KEYS_Default:  # map back to default
            feature_request(self._device, FEATURE.PERSISTENT_REMAPPABLE_ACTION, 0x50, cid, 0xFF)
            self._device.remap_keys._query_key(self.index)
            return self._device.remap_keys.keys[self.index].data_bytes
        else:
            self._actionId, self._code, self._modifierMask = _unpack('!BHB', data_bytes)
            self.cidStatus = 0x01
            feature_request(self._device, FEATURE.PERSISTENT_REMAPPABLE_ACTION, 0x40, cid, 0xFF, data_bytes)
            return True


class KeysArray:
    """A sequence of key mappings supported by a HID++ 2.0 device."""
    def __init__(self, device, count, version):
        assert device is not None
        self.device = device
        self.lock = _threading.Lock()
        if FEATURE.REPROG_CONTROLS_V4 in self.device.features:
            self.keyversion = FEATURE.REPROG_CONTROLS_V4
        elif FEATURE.REPROG_CONTROLS_V2 in self.device.features:
            self.keyversion = FEATURE.REPROG_CONTROLS_V2
        else:
            if _log.isEnabledFor(_ERROR):
                _log.error(f'Trying to read keys on device {device} which has no REPROG_CONTROLS(_VX) support.')
            self.keyversion = None
        self.keys = [None] * count

    def _query_key(self, index: int):
        """Queries the device for a given key and stores it in self.keys."""
        if index < 0 or index >= len(self.keys):
            raise IndexError(index)

        # TODO: add here additional variants for other REPROG_CONTROLS
        if self.keyversion == FEATURE.REPROG_CONTROLS_V2:
            keydata = feature_request(self.device, FEATURE.REPROG_CONTROLS_V2, 0x10, index)
            if keydata:
                cid, tid, flags = _unpack('!HHB', keydata[:5])
                self.keys[index] = ReprogrammableKey(self.device, index, cid, tid, flags)
                self.cid_to_tid[cid] = tid
        elif self.keyversion == FEATURE.REPROG_CONTROLS_V4:
            keydata = feature_request(self.device, FEATURE.REPROG_CONTROLS_V4, 0x10, index)
            if keydata:
                cid, tid, flags1, pos, group, gmask, flags2 = _unpack('!HHBBBBB', keydata[:9])
                flags = flags1 | (flags2 << 8)
                self.keys[index] = ReprogrammableKeyV4(self.device, index, cid, tid, flags, pos, group, gmask)
                self.cid_to_tid[cid] = tid
                if group != 0:  # 0 = does not belong to a group
                    self.group_cids[special_keys.CID_GROUP[group]].append(cid)
        elif _log.isEnabledFor(_WARNING):
            _log.warn(f"Key with index {index} was expected to exist but device doesn't report it.")

    def _ensure_all_keys_queried(self):
        """The retrieval of key information is lazy, but for certain functionality
        we need to know all keys. This function makes sure that's the case."""
        with self.lock:  # don't want two threads doing this
            for (i, k) in enumerate(self.keys):
                if k is None:
                    self._query_key(i)

    def __getitem__(self, index):
        if isinstance(index, int):
            if index < 0 or index >= len(self.keys):
                raise IndexError(index)

            if self.keys[index] is None:
                self._query_key(index)

            return self.keys[index]

        elif isinstance(index, slice):
            indices = index.indices(len(self.keys))
            return [self.__getitem__(i) for i in range(*indices)]

    def index(self, value):
        self._ensure_all_keys_queried()
        for index, k in enumerate(self.keys):
            if k is not None and int(value) == int(k.key):
                return index

    def __iter__(self):
        for k in range(0, len(self.keys)):
            yield self.__getitem__(k)

    def __len__(self):
        return len(self.keys)


class KeysArrayV1(KeysArray):
    def __init__(self, device, count, version=1):
        super().__init__(device, count, version)
        """The mapping from Control IDs to their native Task IDs.
        For example, Control "Left Button" is mapped to Task "Left Click".
        When remapping controls, we point the control we want to remap
        at a target Control ID rather than a target Task ID. This has the
        effect of performing the native task of the target control,
        even if the target itself is also remapped. So remapping
        is not recursive."""
        self.cid_to_tid = {}
        """The mapping from Control ID groups to Controls IDs that belong to it.
        A key k can only be remapped to targets in groups within k.group_mask."""
        self.group_cids = {g: [] for g in special_keys.CID_GROUP}

    def _query_key(self, index: int):
        if index < 0 or index >= len(self.keys):
            raise IndexError(index)
        keydata = feature_request(self.device, FEATURE.REPROG_CONTROLS, 0x10, index)
        if keydata:
            cid, tid, flags = _unpack('!HHB', keydata[:5])
            self.keys[index] = ReprogrammableKey(self.device, index, cid, tid, flags)
            self.cid_to_tid[cid] = tid
        elif _log.isEnabledFor(_WARNING):
            _log.warn(f"Key with index {index} was expected to exist but device doesn't report it.")


class KeysArrayV4(KeysArrayV1):
    def __init__(self, device, count):
        super().__init__(device, count, 4)

    def _query_key(self, index: int):
        if index < 0 or index >= len(self.keys):
            raise IndexError(index)
        keydata = feature_request(self.device, FEATURE.REPROG_CONTROLS_V4, 0x10, index)
        if keydata:
            cid, tid, flags1, pos, group, gmask, flags2 = _unpack('!HHBBBBB', keydata[:9])
            flags = flags1 | (flags2 << 8)
            self.keys[index] = ReprogrammableKeyV4(self.device, index, cid, tid, flags, pos, group, gmask)
            self.cid_to_tid[cid] = tid
            if group != 0:  # 0 = does not belong to a group
                self.group_cids[special_keys.CID_GROUP[group]].append(cid)
        elif _log.isEnabledFor(_WARNING):
            _log.warn(f"Key with index {index} was expected to exist but device doesn't report it.")


# we are only interested in the current host, so use 0xFF for the host throughout
class KeysArrayPersistent(KeysArray):
    def __init__(self, device, count):
        super().__init__(device, count, 5)
        self._capabilities = None

    @property
    def capabilities(self):
        if self._capabilities is None and self.device.online:
            capabilities = self.device.feature_request(FEATURE.PERSISTENT_REMAPPABLE_ACTION, 0x00)
            assert capabilities, 'Oops, persistent remappable key capabilities cannot be retrieved!'
            self._capabilities = _unpack('!H', capabilities[:2])[0]  # flags saying what the mappings are possible
        return self._capabilities

    def _query_key(self, index: int):
        if index < 0 or index >= len(self.keys):
            raise IndexError(index)
        keydata = feature_request(self.device, FEATURE.PERSISTENT_REMAPPABLE_ACTION, 0x20, index, 0xff)
        if keydata:
            key = _unpack('!H', keydata[:2])[0]
            try:
                mapped_data = feature_request(
                    self.device, FEATURE.PERSISTENT_REMAPPABLE_ACTION, 0x30, key & 0xff00, key & 0xff, 0xff
                )
                if mapped_data:
                    _ignore, _ignore, actionId, remapped, modifiers, status = _unpack('!HBBHBB', mapped_data[:8])
            except Exception:
                actionId = remapped = modifiers = status = 0
            actionId = special_keys.ACTIONID[actionId]
            if actionId == special_keys.ACTIONID.Key:
                remapped = special_keys.USB_HID_KEYCODES[remapped]
            elif actionId == special_keys.ACTIONID.Mouse:
                remapped = special_keys.MOUSE_BUTTONS[remapped]
            elif actionId == special_keys.ACTIONID.Hscroll:
                remapped = special_keys.HORIZONTAL_SCROLL[remapped]
            elif actionId == special_keys.ACTIONID.Consumer:
                remapped = special_keys.HID_CONSUMERCODES[remapped]
            elif actionId == special_keys.ACTIONID.Empty:  # purge data from empty value
                remapped = modifiers = 0
            self.keys[index] = PersistentRemappableAction(self.device, index, key, actionId, remapped, modifiers, status)
        elif _log.isEnabledFor(_WARNING):
            _log.warn(f"Key with index {index} was expected to exist but device doesn't report it.")


# Gesture Ids for feature GESTURE_2
GESTURE = _NamedInts(
    Tap1Finger=1,  # task Left_Click
    Tap2Finger=2,  # task Right_Click
    Tap3Finger=3,
    Click1Finger=4,  # task Left_Click
    Click2Finger=5,  # task Right_Click
    Click3Finger=6,
    DoubleTap1Finger=10,
    DoubleTap2Finger=11,
    DoubleTap3Finger=12,
    Track1Finger=20,  # action MovePointer
    TrackingAcceleration=21,
    TapDrag1Finger=30,  # action Drag
    TapDrag2Finger=31,  # action SecondaryDrag
    Drag3Finger=32,
    TapGestures=33,  # group all tap gestures under a single UI setting
    FnClickGestureSuppression=34,  # suppresses Tap and Edge gestures, toggled by Fn+Click
    Scroll1Finger=40,  # action ScrollOrPageXY / ScrollHorizontal
    Scroll2Finger=41,  # action ScrollOrPageXY / ScrollHorizontal
    Scroll2FingerHoriz=42,  # action ScrollHorizontal
    Scroll2FingerVert=43,  # action WheelScrolling
    Scroll2FingerStateless=44,
    NaturalScrolling=45,  # affects native HID wheel reporting by gestures, not when diverted
    Thumbwheel=46,  # action WheelScrolling
    VScrollInertia=48,
    VScrollBallistics=49,
    Swipe2FingerHoriz=50,  # action PageScreen
    Swipe3FingerHoriz=51,  # action PageScreen
    Swipe4FingerHoriz=52,  # action PageScreen
    Swipe3FingerVert=53,
    Swipe4FingerVert=54,
    LeftEdgeSwipe1Finger=60,
    RightEdgeSwipe1Finger=61,
    BottomEdgeSwipe1Finger=62,
    TopEdgeSwipe1Finger=63,
    LeftEdgeSwipe1Finger2=64,  # task HorzScrollNoRepeatSet
    RightEdgeSwipe1Finger2=65,  # task 122 ??
    BottomEdgeSwipe1Finger2=66,  #
    TopEdgeSwipe1Finger2=67,  # task 121 ??
    LeftEdgeSwipe2Finger=70,
    RightEdgeSwipe2Finger=71,
    BottomEdgeSwipe2Finger=72,
    TopEdgeSwipe2Finger=73,
    Zoom2Finger=80,  # action Zoom
    Zoom2FingerPinch=81,  # ZoomBtnInSet
    Zoom2FingerSpread=82,  # ZoomBtnOutSet
    Zoom3Finger=83,
    Zoom2FingerStateless=84,  # action Zoom
    TwoFingersPresent=85,
    Rotate2Finger=87,
    Finger1=90,
    Finger2=91,
    Finger3=92,
    Finger4=93,
    Finger5=94,
    Finger6=95,
    Finger7=96,
    Finger8=97,
    Finger9=98,
    Finger10=99,
    DeviceSpecificRawData=100,
)
GESTURE._fallback = lambda x: 'unknown:%04X' % x

# Param Ids for feature GESTURE_2
PARAM = _NamedInts(
    ExtraCapabilities=1,  # not suitable for use
    PixelZone=2,  # 4 2-byte integers, left, bottom, width, height; pixels
    RatioZone=3,  # 4 bytes, left, bottom, width, height; unit 1/240 pad size
    ScaleFactor=4,  # 2-byte integer, with 256 as normal scale
)
PARAM._fallback = lambda x: 'unknown:%04X' % x


class SubParam:
    __slots__ = ('id', 'length', 'minimum', 'maximum', 'widget')

    def __init__(self, id, length, minimum=None, maximum=None, widget=None):
        self.id = id
        self.length = length
        self.minimum = minimum if minimum is not None else 0
        self.maximum = maximum if maximum is not None else ((1 << 8 * length) - 1)
        self.widget = widget if widget is not None else 'Scale'

    def __str__(self):
        return self.id

    def __repr__(self):
        return self.id


SUB_PARAM = {   # (byte count, minimum, maximum)
    PARAM['ExtraCapabilities']: None,  # ignore
    PARAM['PixelZone']: (  # TODO: replace min and max with the correct values
        SubParam('left', 2, 0x0000, 0xFFFF, 'SpinButton'),
        SubParam('bottom', 2, 0x0000, 0xFFFF, 'SpinButton'),
        SubParam('width', 2, 0x0000, 0xFFFF, 'SpinButton'),
        SubParam('height', 2, 0x0000, 0xFFFF, 'SpinButton')),
    PARAM['RatioZone']: (  # TODO: replace min and max with the correct values
        SubParam('left', 1, 0x00, 0xFF, 'SpinButton'),
        SubParam('bottom', 1, 0x00, 0xFF, 'SpinButton'),
        SubParam('width', 1, 0x00, 0xFF, 'SpinButton'),
        SubParam('height', 1, 0x00, 0xFF, 'SpinButton')),
    PARAM['ScaleFactor']: (
        SubParam('scale', 2, 0x002E, 0x01FF, 'Scale'), )
}

# Spec Ids for feature GESTURE_2
SPEC = _NamedInts(
    DVI_field_width=1,
    field_widths=2,
    period_unit=3,
    resolution=4,
    multiplier=5,
    sensor_size=6,
    finger_width_and_height=7,
    finger_major_minor_axis=8,
    finger_force=9,
    zone=10
)
SPEC._fallback = lambda x: 'unknown:%04X' % x

# Action Ids for feature GESTURE_2
ACTION_ID = _NamedInts(
    MovePointer=1,
    ScrollHorizontal=2,
    WheelScrolling=3,
    ScrollVertial=4,
    ScrollOrPageXY=5,
    ScrollOrPageHorizontal=6,
    PageScreen=7,
    Drag=8,
    SecondaryDrag=9,
    Zoom=10,
    ScrollHorizontalOnly=11,
    ScrollVerticalOnly=12
)
ACTION_ID._fallback = lambda x: 'unknown:%04X' % x


class Gesture:
    def __init__(self, device, low, high, next_index, next_diversion_index):
        self._device = device
        self.id = low
        self.gesture = GESTURE[low]
        self.can_be_enabled = high & 0x01
        self.can_be_diverted = high & 0x02
        self.show_in_ui = high & 0x04
        self.desired_software_default = high & 0x08
        self.persistent = high & 0x10
        self.default_enabled = high & 0x20
        self.index = next_index if self.can_be_enabled or self.default_enabled else None
        self.diversion_index = next_diversion_index if self.can_be_diverted else None
        self._enabled = None
        self._diverted = None

    def _offset_mask(self, index):  # offset and mask
        if index is not None:
            offset = index >> 3  # 8 gestures per byte
            mask = 0x1 << (index % 8)
            return (offset, mask)
        else:
            return (None, None)

    enable_offset_mask = lambda gesture: gesture._offset_mask(gesture.index)

    diversion_offset_mask = lambda gesture: gesture._offset_mask(gesture.diversion_index)

    def enabled(self):  # is the gesture enabled?
        if self._enabled is None and self.index is not None:
            offset, mask = self.enable_offset_mask()
            result = feature_request(self._device, FEATURE.GESTURE_2, 0x10, offset, 0x01, mask)
            self._enabled = bool(result[0] & mask) if result else None
        return self._enabled

    def set(self, enable):  # enable or disable the gesture
        if not self.can_be_enabled:
            return None
        if self.index is not None:
            offset, mask = self.enable_offset_mask()
            reply = feature_request(self._device, FEATURE.GESTURE_2, 0x20, offset, 0x01, mask, mask if enable else 0x00)
            return reply

    def diverted(self):  # is the gesture diverted?
        if self._diverted is None and self.diversion_index is not None:
            offset, mask = self.diversion_offset_mask()
            result = feature_request(self._device, FEATURE.GESTURE_2, 0x30, offset, 0x01, mask)
            self._diverted = bool(result[0] & mask) if result else None
        return self._diverted

    def divert(self, diverted):  # divert or undivert the gesture
        if not self.can_be_diverted:
            return None
        if self.diversion_index is not None:
            offset, mask = self.diversion_offset_mask()
            reply = feature_request(self._device, FEATURE.GESTURE_2, 0x40, offset, 0x01, mask, mask if diverted else 0x00)
            return reply

    def as_int(self):
        return self.gesture

    def __int__(self):
        return self.id

    def __repr__(self):
        return f'<Gesture {self.gesture} index={self.index} diversion_index={self.diversion_index}>'

    # allow a gesture to be used as a settings reader/writer to enable and disable the gesture
    read = enabled
    write = set


class Param:
    param_index = {}

    def __init__(self, device, low, high):
        self._device = device
        self.id = low
        self.param = PARAM[low]
        self.size = high & 0x0F
        self.show_in_ui = bool(high & 0x1F)
        self._value = None
        self._default_value = None
        self.index = Param.param_index.get(device, 0)
        Param.param_index[device] = self.index + 1

    @property
    def sub_params(self):
        return SUB_PARAM.get(self.id, None)

    @property
    def value(self):
        return self._value if self._value is not None else self.read()

    def read(self):  # returns the bytes for the parameter
        result = feature_request(self._device, FEATURE.GESTURE_2, 0x70, self.index, 0xFF)
        if result:
            self._value = _bytes2int(result[:self.size])
            return self._value

    @property
    def default_value(self):
        if self._default_value is None:
            self._default_value = self._read_default()
        return self._default_value

    def _read_default(self):
        result = feature_request(self._device, FEATURE.GESTURE_2, 0x60, self.index, 0xFF)
        if result:
            self._default_value = _bytes2int(result[:self.size])
            return self._default_value

    def write(self, bytes):
        self._value = bytes
        return feature_request(self._device, FEATURE.GESTURE_2, 0x80, self.index, bytes, 0xFF)

    def __str__(self):
        return str(self.param)

    def __int__(self):
        return self.id


class Spec:
    def __init__(self, device, low, high):
        self._device = device
        self.id = low
        self.spec = SPEC[low]
        self.byte_count = high & 0x0F
        self._value = None

    @property
    def value(self):
        if self._value is None:
            self._value = self.read()
        return self._value

    def read(self):
        try:
            value = feature_request(self._device, FEATURE.GESTURE_2, 0x50, self.id, 0xFF)
        except FeatureCallError:  # some calls produce an error (notably spec 5 multiplier on K400Plus)
            if _log.isEnabledFor(_WARNING):
                _log.warn(f'Feature Call Error reading Gesture Spec on device {self._device} for spec {self.id} - use None')
            return None
        return _bytes2int(value[:self.byte_count])

    def __repr__(self):
        return f'[{self.spec}={self.value}]'


class Gestures:
    """Information about the gestures that a device supports.
    Right now only some information fields are supported.
    WARNING: Assumes that parameters are always global, which is not the case.
    """
    def __init__(self, device):
        self.device = device
        self.gestures = {}
        self.params = {}
        self.specs = {}
        index = 0
        next_gesture_index = next_divsn_index = 0
        field_high = 0x00
        while field_high != 0x01:  # end of fields
            # retrieve the next eight fields
            fields = feature_request(device, FEATURE.GESTURE_2, 0x00, index >> 8, index & 0xFF)
            if not fields:
                break
            for offset in range(8):
                field_high = fields[offset * 2]
                field_low = fields[offset * 2 + 1]
                if field_high == 0x1:  # end of fields
                    break
                elif field_high & 0x80:
                    gesture = Gesture(device, field_low, field_high, next_gesture_index, next_divsn_index)
                    next_gesture_index = next_gesture_index if gesture.index is None else next_gesture_index + 1
                    next_divsn_index = next_divsn_index if gesture.diversion_index is None else next_divsn_index + 1
                    self.gestures[gesture.gesture] = gesture
                elif field_high & 0xF0 == 0x30 or field_high & 0xF0 == 0x20:
                    param = Param(device, field_low, field_high)
                    self.params[param.param] = param
                elif field_high == 0x04:
                    if field_low != 0x00:
                        _log.error(f'Unimplemented GESTURE_2 grouping {field_low} {field_high} found.')
                elif field_high & 0xF0 == 0x40:
                    spec = Spec(device, field_low, field_high)
                    self.specs[spec.spec] = spec
                else:
                    _log.warn(f'Unimplemented GESTURE_2 field {field_low} {field_high} found.')
                index += 1

    def gesture(self, gesture):
        return self.gestures.get(gesture, None)

    def gesture_enabled(self, gesture):  # is the gesture enabled?
        g = self.gestures.get(gesture, None)
        return g.enabled(self.device) if g else None

    def enable_gesture(self, gesture):
        g = self.gestures.get(gesture, None)
        return g.set(self.device, True) if g else None

    def disable_gesture(self, gesture):
        g = self.gestures.get(gesture, None)
        return g.set(self.device, False) if g else None

    def param(self, param):
        return self.params.get(param, None)

    def get_param(self, param):
        g = self.params.get(param, None)
        return g.get(self.device) if g else None

    def set_param(self, param, value):
        g = self.params.get(param, None)
        return g.set(self.device, value) if g else None


#
#
#


def feature_request(device, feature, function=0x00, *params, no_reply=False):
    if device.online and device.features:
        if feature in device.features:
            feature_index = device.features[feature]
            return device.request((feature_index << 8) + (function & 0xFF), *params, no_reply=no_reply)


def get_firmware(device):
    """Reads a device's firmware info.

    :returns: a list of FirmwareInfo tuples, ordered by firmware layer.
    """
    count = feature_request(device, FEATURE.DEVICE_FW_VERSION)
    if count:
        count = ord(count[:1])

        fw = []
        for index in range(0, count):
            fw_info = feature_request(device, FEATURE.DEVICE_FW_VERSION, 0x10, index)
            if fw_info:
                level = ord(fw_info[:1]) & 0x0F
                if level == 0 or level == 1:
                    name, version_major, version_minor, build = _unpack('!3sBBH', fw_info[1:8])
                    version = '%02X.%02X' % (version_major, version_minor)
                    if build:
                        version += '.B%04X' % build
                    extras = fw_info[9:].rstrip(b'\x00') or None
                    fw_info = _FirmwareInfo(FIRMWARE_KIND[level], name.decode('ascii'), version, extras)
                elif level == FIRMWARE_KIND.Hardware:
                    fw_info = _FirmwareInfo(FIRMWARE_KIND.Hardware, '', str(ord(fw_info[1:2])), None)
                else:
                    fw_info = _FirmwareInfo(FIRMWARE_KIND.Other, '', '', None)

                fw.append(fw_info)
                # if _log.isEnabledFor(_DEBUG):
                #     _log.debug("device %d firmware %s", devnumber, fw_info)
        return tuple(fw)


def get_ids(device):
    """Reads a device's ids (unit and model numbers)"""
    ids = feature_request(device, FEATURE.DEVICE_FW_VERSION)
    if ids:
        unitId = ids[1:5]
        modelId = ids[7:13]
        transport_bits = ord(ids[6:7])
        offset = 0
        tid_map = {}
        for transport, flag in [('btid', 0x1), ('btleid', 0x02), ('wpid', 0x04), ('usbid', 0x08)]:
            if transport_bits & flag:
                tid_map[transport] = modelId[offset:offset + 2].hex().upper()
                offset = offset + 2
        return (unitId.hex().upper(), modelId.hex().upper(), tid_map)


def get_kind(device):
    """Reads a device's type.

    :see DEVICE_KIND:
    :returns: a string describing the device type, or ``None`` if the device is
    not available or does not support the ``DEVICE_NAME`` feature.
    """
    kind = feature_request(device, FEATURE.DEVICE_NAME, 0x20)
    if kind:
        kind = ord(kind[:1])
        # if _log.isEnabledFor(_DEBUG):
        #     _log.debug("device %d type %d = %s", devnumber, kind, DEVICE_KIND[kind])
        return DEVICE_KIND[kind]


def get_name(device):
    """Reads a device's name.

    :returns: a string with the device name, or ``None`` if the device is not
    available or does not support the ``DEVICE_NAME`` feature.
    """
    name_length = feature_request(device, FEATURE.DEVICE_NAME)
    if name_length:
        name_length = ord(name_length[:1])

        name = b''
        while len(name) < name_length:
            fragment = feature_request(device, FEATURE.DEVICE_NAME, 0x10, len(name))
            if fragment:
                name += fragment[:name_length - len(name)]
            else:
                _log.error('failed to read whole name of %s (expected %d chars)', device, name_length)
                return None

        return name.decode('utf-8')


def get_friendly_name(device):
    """Reads a device's friendly name.

    :returns: a string with the device name, or ``None`` if the device is not
    available or does not support the ``DEVICE_NAME`` feature.
    """
    name_length = feature_request(device, FEATURE.DEVICE_FRIENDLY_NAME)
    if name_length:
        name_length = ord(name_length[:1])

        name = b''
        while len(name) < name_length:
            fragment = feature_request(device, FEATURE.DEVICE_FRIENDLY_NAME, 0x10, len(name))
            if fragment:
                initial_null = 0 if fragment[0] else 1  # initial null actually seen on a device
                name += fragment[initial_null:name_length + initial_null - len(name)]
            else:
                _log.error('failed to read whole name of %s (expected %d chars)', device, name_length)
                return None

        return name.decode('utf-8')


def get_battery_status(device):
    report = feature_request(device, FEATURE.BATTERY_STATUS)
    if report:
        return decipher_battery_status(report)


def decipher_battery_status(report):
    discharge, next, status = _unpack('!BBB', report[:3])
    discharge = None if discharge == 0 else discharge
    status = BATTERY_STATUS[status]
    if _log.isEnabledFor(_DEBUG):
        _log.debug('battery status %s%% charged, next %s%%, status %s', discharge, next, status)
    return FEATURE.BATTERY_STATUS, discharge, next, status, None


def get_battery_unified(device):
    report = feature_request(device, FEATURE.UNIFIED_BATTERY, 0x10)
    if report is not None:
        return decipher_battery_unified(report)


def decipher_battery_unified(report):
    discharge, level, status, _ignore = _unpack('!BBBB', report[:4])
    status = BATTERY_STATUS[status]
    if _log.isEnabledFor(_DEBUG):
        _log.debug('battery unified %s%% charged, level %s, charging %s', discharge, level, status)
    level = (
        _BATTERY_APPROX.full if level == 8  # full
        else _BATTERY_APPROX.good if level == 4  # good
        else _BATTERY_APPROX.low if level == 2  # low
        else _BATTERY_APPROX.critical if level == 1  # critical
        else _BATTERY_APPROX.empty
    )
    return FEATURE.UNIFIED_BATTERY, discharge if discharge else level, None, status, None


# voltage to remaining charge from Logitech
battery_voltage_remaining = (
    (4186, 100),
    (4067, 90),
    (3989, 80),
    (3922, 70),
    (3859, 60),
    (3811, 50),
    (3778, 40),
    (3751, 30),
    (3717, 20),
    (3671, 10),
    (3646, 5),
    (3579, 2),
    (3500, 0),
    (-1000, 0),
)


def get_battery_voltage(device):
    report = feature_request(device, FEATURE.BATTERY_VOLTAGE)
    if report is not None:
        return decipher_battery_voltage(report)


def decipher_battery_voltage(report):
    voltage, flags = _unpack('>HB', report[:3])
    status = BATTERY_STATUS.discharging
    charge_sts = ERROR.unknown
    charge_lvl = CHARGE_LEVEL.average
    charge_type = CHARGE_TYPE.standard
    if flags & (1 << 7):
        status = BATTERY_STATUS.recharging
        charge_sts = CHARGE_STATUS[flags & 0x03]
    if charge_sts is None:
        charge_sts = ERROR.unknown
    elif charge_sts == CHARGE_STATUS.full:
        charge_lvl = CHARGE_LEVEL.full
        status = BATTERY_STATUS.full
    if (flags & (1 << 3)):
        charge_type = CHARGE_TYPE.fast
    elif (flags & (1 << 4)):
        charge_type = CHARGE_TYPE.slow
        status = BATTERY_STATUS.slow_recharge
    elif (flags & (1 << 5)):
        charge_lvl = CHARGE_LEVEL.critical
    for level in battery_voltage_remaining:
        if level[0] < voltage:
            charge_lvl = level[1]
            break
    if _log.isEnabledFor(_DEBUG):
        _log.debug(
            'battery voltage %d mV, charging %s, status %d = %s, level %s, type %s', voltage, status, (flags & 0x03),
            charge_sts, charge_lvl, charge_type
        )
    return FEATURE.BATTERY_VOLTAGE, charge_lvl, None, status, voltage


def get_adc_measurement(device):
    try:  # this feature call produces an error for headsets that are connected but inactive
        report = feature_request(device, FEATURE.ADC_MEASUREMENT)
        if report is not None:
            return decipher_adc_measurement(report)
    except FeatureCallError:
        return FEATURE.ADC_MEASUREMENT if FEATURE.ADC_MEASUREMENT in device.features else None


def decipher_adc_measurement(report):
    # partial implementation - needs mapping to levels
    adc, flags = _unpack('!HB', report[:3])
    for level in battery_voltage_remaining:
        if level[0] < adc:
            charge_level = level[1]
            break
    if flags & 0x01:
        status = BATTERY_STATUS.recharging if flags & 0x02 else BATTERY_STATUS.discharging
        return FEATURE.ADC_MEASUREMENT, charge_level, None, status, adc


battery_functions = {
    FEATURE.BATTERY_STATUS: get_battery_status,
    FEATURE.BATTERY_VOLTAGE: get_battery_voltage,
    FEATURE.UNIFIED_BATTERY: get_battery_unified,
    FEATURE.ADC_MEASUREMENT: get_adc_measurement,
}


def get_battery(device, feature):
    """Return battery information - feature, approximate level, next, charging, voltage
    or battery feature if there is one but it is not responding or None for no battery feature"""
    if feature is not None:
        battery_function = battery_functions.get(feature, None)
        if battery_function:
            result = battery_function(device)
            if result:
                return result
    else:
        for battery_function in battery_functions.values():
            result = battery_function(device)
            if result:
                return result
    return 0


def get_keys(device):
    # TODO: add here additional variants for other REPROG_CONTROLS
    count = None
    if FEATURE.REPROG_CONTROLS_V2 in device.features:
        count = feature_request(device, FEATURE.REPROG_CONTROLS_V2)
        return KeysArrayV1(device, ord(count[:1]))
    elif FEATURE.REPROG_CONTROLS_V4 in device.features:
        count = feature_request(device, FEATURE.REPROG_CONTROLS_V4)
        return KeysArrayV4(device, ord(count[:1]))
    return None


def get_remap_keys(device):
    count = feature_request(device, FEATURE.PERSISTENT_REMAPPABLE_ACTION, 0x10)
    if count:
        return KeysArrayPersistent(device, ord(count[:1]))


def get_gestures(device):
    if getattr(device, '_gestures', None) is not None:
        return device._gestures
    if FEATURE.GESTURE_2 in device.features:
        return Gestures(device)


def get_mouse_pointer_info(device):
    pointer_info = feature_request(device, FEATURE.MOUSE_POINTER)
    if pointer_info:
        dpi, flags = _unpack('!HB', pointer_info[:3])
        acceleration = ('none', 'low', 'med', 'high')[flags & 0x3]
        suggest_os_ballistics = (flags & 0x04) != 0
        suggest_vertical_orientation = (flags & 0x08) != 0
        return {
            'dpi': dpi,
            'acceleration': acceleration,
            'suggest_os_ballistics': suggest_os_ballistics,
            'suggest_vertical_orientation': suggest_vertical_orientation
        }


def get_vertical_scrolling_info(device):
    vertical_scrolling_info = feature_request(device, FEATURE.VERTICAL_SCROLLING)
    if vertical_scrolling_info:
        roller, ratchet, lines = _unpack('!BBB', vertical_scrolling_info[:3])
        roller_type = (
            'reserved', 'standard', 'reserved', '3G', 'micro', 'normal touch pad', 'inverted touch pad', 'reserved'
        )[roller]
        return {'roller': roller_type, 'ratchet': ratchet, 'lines': lines}


def get_hi_res_scrolling_info(device):
    hi_res_scrolling_info = feature_request(device, FEATURE.HI_RES_SCROLLING)
    if hi_res_scrolling_info:
        mode, resolution = _unpack('!BB', hi_res_scrolling_info[:2])
        return mode, resolution


def get_pointer_speed_info(device):
    pointer_speed_info = feature_request(device, FEATURE.POINTER_SPEED)
    if pointer_speed_info:
        pointer_speed_hi, pointer_speed_lo = _unpack('!BB', pointer_speed_info[:2])
        # if pointer_speed_lo > 0:
        #     pointer_speed_lo = pointer_speed_lo
        return pointer_speed_hi + pointer_speed_lo / 256


def get_lowres_wheel_status(device):
    lowres_wheel_status = feature_request(device, FEATURE.LOWRES_WHEEL)
    if lowres_wheel_status:
        wheel_flag = _unpack('!B', lowres_wheel_status[:1])[0]
        wheel_reporting = ('HID', 'HID++')[wheel_flag & 0x01]
        return wheel_reporting


def get_hires_wheel(device):
    caps = feature_request(device, FEATURE.HIRES_WHEEL, 0x00)
    mode = feature_request(device, FEATURE.HIRES_WHEEL, 0x10)
    ratchet = feature_request(device, FEATURE.HIRES_WHEEL, 0x030)

    if caps and mode and ratchet:
        # Parse caps
        multi, flags = _unpack('!BB', caps[:2])

        has_invert = (flags & 0x08) != 0
        has_ratchet = (flags & 0x04) != 0

        # Parse mode
        wheel_mode, reserved = _unpack('!BB', mode[:2])

        target = (wheel_mode & 0x01) != 0
        res = (wheel_mode & 0x02) != 0
        inv = (wheel_mode & 0x04) != 0

        # Parse Ratchet switch
        ratchet_mode, reserved = _unpack('!BB', ratchet[:2])

        ratchet = (ratchet_mode & 0x01) != 0

        return multi, has_invert, has_ratchet, inv, res, target, ratchet


def get_new_fn_inversion(device):
    state = feature_request(device, FEATURE.NEW_FN_INVERSION, 0x00)
    if state:
        inverted, default_inverted = _unpack('!BB', state[:2])
        inverted = (inverted & 0x01) != 0
        default_inverted = (default_inverted & 0x01) != 0
        return inverted, default_inverted


def get_host_names(device):
    state = feature_request(device, FEATURE.HOSTS_INFO, 0x00)
    host_names = {}
    if state:
        capability_flags, _ignore, numHosts, currentHost = _unpack('!BBBB', state[:4])
        if capability_flags & 0x01:  # device can get host names
            for host in range(0, numHosts):
                hostinfo = feature_request(device, FEATURE.HOSTS_INFO, 0x10, host)
                _ignore, status, _ignore, _ignore, nameLen, _ignore = _unpack('!BBBBBB', hostinfo[:6])
                name = ''
                remaining = nameLen
                while remaining > 0:
                    name_piece = feature_request(device, FEATURE.HOSTS_INFO, 0x30, host, nameLen - remaining)
                    if name_piece:
                        name += name_piece[2:2 + min(remaining, 14)].decode()
                        remaining = max(0, remaining - 14)
                    else:
                        remaining = 0
                host_names[host] = (bool(status), name)
        # update the current host's name if it doesn't match the system name
        import socket
        hostname = socket.gethostname().partition('.')[0]
        if host_names[currentHost][1] != hostname:
            set_host_name(device, hostname, host_names[currentHost][1])
            host_names[currentHost] = (host_names[currentHost][0], hostname)
    return host_names


def set_host_name(device, name, currentName=''):
    name = bytearray(name, 'utf-8')
    currentName = bytearray(currentName, 'utf-8')
    if _log.isEnabledFor(_INFO):
        _log.info('Setting host name to %s', name)
    state = feature_request(device, FEATURE.HOSTS_INFO, 0x00)
    if state:
        flags, _ignore, _ignore, currentHost = _unpack('!BBBB', state[:4])
        if flags & 0x02:
            hostinfo = feature_request(device, FEATURE.HOSTS_INFO, 0x10, currentHost)
            _ignore, _ignore, _ignore, _ignore, _ignore, maxNameLen = _unpack('!BBBBBB', hostinfo[:6])
            if name[:maxNameLen] == currentName[:maxNameLen] and False:
                return True
            length = min(maxNameLen, len(name))
            chunk = 0
            while chunk < length:
                response = feature_request(device, FEATURE.HOSTS_INFO, 0x40, currentHost, chunk, name[chunk:chunk + 14])
                if not response:
                    return False
                chunk += 14
        return True


def get_onboard_mode(device):
    state = feature_request(device, FEATURE.ONBOARD_PROFILES, 0x20)

    if state:
        mode = _unpack('!B', state[:1])[0]
        return mode


def set_onboard_mode(device, mode):
    state = feature_request(device, FEATURE.ONBOARD_PROFILES, 0x10, mode)
    return state


def get_polling_rate(device):
    state = feature_request(device, FEATURE.REPORT_RATE, 0x10)
    if state:
        rate = _unpack('!B', state[:1])[0]
        return rate


def get_remaining_pairing(device):
    result = feature_request(device, FEATURE.REMAINING_PAIRING, 0x0)
    if result:
        result = _unpack('!B', result[:1])[0]
        return result
