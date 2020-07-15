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

from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from logging import DEBUG as _DEBUG
from logging import getLogger

from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20
from . import special_keys as _special_keys
from .common import NamedInt as _NamedInt
from .common import NamedInts as _NamedInts
from .common import bytes2int as _bytes2int
from .common import int2bytes as _int2bytes
from .common import unpack as _unpack
from .i18n import _
from .settings import KIND as _KIND
from .settings import BitFieldSetting as _BitFieldSetting
from .settings import BitFieldValidator as _BitFieldV
from .settings import BooleanValidator as _BooleanV
from .settings import ChoicesMapValidator as _ChoicesMapV
from .settings import ChoicesValidator as _ChoicesV
from .settings import FeatureRW as _FeatureRW
from .settings import FeatureRWMap as _FeatureRWMap
from .settings import RangeValidator as _RangeV
from .settings import RegisterRW as _RegisterRW
from .settings import Setting as _Setting
from .settings import Settings as _Settings

_log = getLogger(__name__)
del getLogger

_DK = _hidpp10.DEVICE_KIND
_R = _hidpp10.REGISTERS
_F = _hidpp20.FEATURE

#
# pre-defined basic setting descriptors
#


def register_toggle(
    name,
    register,
    true_value=_BooleanV.default_true,
    false_value=_BooleanV.default_false,
    mask=_BooleanV.default_mask,
    label=None,
    description=None,
    device_kind=None
):
    validator = _BooleanV(true_value=true_value, false_value=false_value, mask=mask)
    rw = _RegisterRW(register)
    return _Setting(name, rw, validator, label=label, description=description, device_kind=device_kind)


def register_choices(name, register, choices, kind=_KIND.choice, label=None, description=None, device_kind=None):
    assert choices
    validator = _ChoicesV(choices)
    rw = _RegisterRW(register)
    return _Setting(name, rw, validator, kind=kind, label=label, description=description, device_kind=device_kind)


def feature_toggle(
    name,
    feature,
    read_fnid=_FeatureRW.default_read_fnid,
    write_fnid=_FeatureRW.default_write_fnid,
    true_value=_BooleanV.default_true,
    false_value=_BooleanV.default_false,
    mask=_BooleanV.default_mask,
    label=None,
    description=None,
    device_kind=None
):
    validator = _BooleanV(true_value=true_value, false_value=false_value, mask=mask)
    rw = _FeatureRW(feature, read_fnid=read_fnid, write_fnid=write_fnid)
    return _Setting(name, rw, validator, feature=feature, label=label, description=description, device_kind=device_kind)


def feature_bitfield_toggle(
    name,
    feature,
    options,
    read_fnid=_FeatureRW.default_read_fnid,
    write_fnid=_FeatureRW.default_write_fnid,
    label=None,
    description=None,
    device_kind=None
):
    assert options
    validator = _BitFieldV(options)
    rw = _FeatureRW(feature, read_fnid=read_fnid, write_fnid=write_fnid)
    return _BitFieldSetting(
        name, rw, validator, feature=feature, label=label, description=description, device_kind=device_kind
    )


def feature_bitfield_toggle_dynamic(
    name,
    feature,
    options_callback,
    read_fnid=_FeatureRW.default_read_fnid,
    write_fnid=_FeatureRW.default_write_fnid,
    label=None,
    description=None,
    device_kind=None
):
    def instantiate(device):
        options = options_callback(device)
        setting = feature_bitfield_toggle(
            name,
            feature,
            options,
            read_fnid=read_fnid,
            write_fnid=write_fnid,
            label=label,
            description=description,
            device_kind=device_kind
        )
        return setting(device)

    instantiate._rw_kind = _FeatureRW.kind
    return instantiate


def feature_choices(name, feature, choices, **kwargs):
    assert choices
    validator = _ChoicesV(choices, **kwargs)
    rw = _FeatureRW(feature, **kwargs)
    return _Setting(name, rw, validator, feature=feature, kind=_KIND.choice, **kwargs)


def feature_choices_dynamic(name, feature, choices_callback, **kwargs):
    # Proxy that obtains choices dynamically from a device
    def instantiate(device):
        # Obtain choices for this feature
        choices = choices_callback(device)
        if not choices:  # no choices, so don't create a setting
            return None
        setting = feature_choices(name, feature, choices, **kwargs)
        return setting(device)

    instantiate._rw_kind = _FeatureRW.kind
    return instantiate


# maintain a mapping from keys (NamedInts) to one of a list of choices (NamedInts), default is first one
# the setting is stored as a JSON-compatible object mapping the key int (as a string) to the choice int
def feature_map_choices(name, feature, choicesmap, **kwargs):
    assert choicesmap
    validator = _ChoicesMapV(choicesmap, **kwargs)
    rw = _FeatureRWMap(feature, **kwargs)
    return _Settings(name, rw, validator, feature=feature, kind=_KIND.map_choice, **kwargs)


def feature_map_choices_dynamic(name, feature, choices_callback, **kwargs):
    # Proxy that obtains choices dynamically from a device
    def instantiate(device):
        choices = choices_callback(device)
        if not choices:  # no choices, so don't create a Setting
            return None
        setting = feature_map_choices(name, feature, choices, **kwargs)
        return setting(device)

    instantiate._rw_kind = _FeatureRWMap.kind
    return instantiate


def feature_range(
    name,
    feature,
    min_value,
    max_value,
    read_fnid=_FeatureRW.default_read_fnid,
    write_fnid=_FeatureRW.default_write_fnid,
    rw=None,
    bytes_count=None,
    label=None,
    description=None,
    device_kind=None
):
    validator = _RangeV(min_value, max_value, bytes_count=bytes_count)
    if rw is None:
        rw = _FeatureRW(feature, read_fnid=read_fnid, write_fnid=write_fnid)
    return _Setting(
        name, rw, validator, feature=feature, kind=_KIND.range, label=label, description=description, device_kind=device_kind
    )


#
# common strings for settings - name, string to display in main window, tool tip for main window
#

_HAND_DETECTION = ('hand-detection', _('Hand Detection'), _('Turn on illumination when the hands hover over the keyboard.'))
_SMOOTH_SCROLL = ('smooth-scroll', _('Smooth Scrolling'), _('High-sensitivity mode for vertical scroll with the wheel.'))
_SIDE_SCROLL = (
    'side-scroll', _('Side Scrolling'),
    _(
        'When disabled, pushing the wheel sideways sends custom button events\n'
        'instead of the standard side-scrolling events.'
    )
)
_HI_RES_SCROLL = (
    'hi-res-scroll', _('High Resolution Scrolling'), _('High-sensitivity mode for vertical scroll with the wheel.')
)
_LOW_RES_SCROLL = (
    'lowres-smooth-scroll', _('HID++ Scrolling'),
    _('HID++ mode for vertical scroll with the wheel.') + '\n' + _('Effectively turns off wheel scrolling in Linux.')
)
_HIRES_INV = (
    'hires-smooth-invert', _('High Resolution Wheel Invert'),
    _('High-sensitivity wheel invert direction for vertical scroll.')
)
_HIRES_RES = ('hires-smooth-resolution', _('Wheel Resolution'), _('High-sensitivity mode for vertical scroll with the wheel.'))
_FN_SWAP = (
    'fn-swap', _('Swap Fx function'),
    _(
        'When set, the F1..F12 keys will activate their special function,\n'
        'and you must hold the FN key to activate their standard function.'
    ) + '\n\n' + _(
        'When unset, the F1..F12 keys will activate their standard function,\n'
        'and you must hold the FN key to activate their special function.'
    )
)
_DPI = ('dpi', _('Sensitivity (DPI)'), None)
_POINTER_SPEED = (
    'pointer_speed', _('Sensitivity (Pointer Speed)'), _('Speed multiplier for mouse (256 is normal multiplier).')
)
_SMART_SHIFT = (
    'smart-shift', _('Smart Shift'),
    _(
        'Automatically switch the mouse wheel between ratchet and freespin mode.\n'
        'The mouse wheel is always free at 0, and always locked at 50'
    )
)
_BACKLIGHT = ('backlight', _('Backlight'), _('Turn illumination on or off on keyboard.'))
_REPROGRAMMABLE_KEYS = (
    'reprogrammable-keys', _('Actions'), _('Change the action for the key or button.') + '\n' +
    _('Changing important actions (such as for the left mouse button) can result in an unusable system.')
)
_DISABLE_KEYS = ('disable-keyboard-keys', _('Disable keys'), _('Disable specific keyboard keys.'))
_PLATFORM = ('multiplatform', _('Set OS'), _('Change keys to match OS.'))
_CHANGE_HOST = ('change-host', _('Change Host'), _('Switch connection to a different host'))
_THUMB_SCROLL_MODE = (
    'thumb-scroll-mode', _('HID++ Thumb Scrolling'),
    _('HID++ mode for horizontal scroll with the thumb wheel.') + '\n' + _('Effectively turns off thumb scrolling in Linux.')
)
_THUMB_SCROLL_INVERT = ('thumb-scroll-invert', _('Thumb Scroll Invert'), _('Invert thumb scroll direction.'))

#
# Keyword arguments for setting template functions:
#  label='', description='' - label and tooltip to be shown in GUI
#  persist=True - whether to store the values and reapply them from now on
#  device_kind - the kinds of devices that setting is suitable for (NOT CURRENTLY USED)
#  read_fnid=0x00, write_fnid=0x10 - default 0x00 and 0x10 function numbers (times 16) to read and write setting
#  bytes_count=1 - number of bytes for the data (ignoring the key, if any)
# only for boolean settings
#  true_value=0x01, false_value=0x00,  mask=0xFF - integer or byte strings for boolean settings
# only for map choices
#  key_bytes_count=1 - number of bytes in the key
#  extra_default - extra value that cannot be set but means same as default value
# only for choices and map choices
#  read_skip_bytes_count=0 - number of bytes to ignore before the data when reading
#  write_prefix_bytes=b'' - bytes to put before the data writing


def _register_hand_detection(
    register=_R.keyboard_hand_detection, true_value=b'\x00\x00\x00', false_value=b'\x00\x00\x30', mask=b'\x00\x00\xFF'
):
    return register_toggle(
        _HAND_DETECTION[0],
        register,
        true_value=true_value,
        false_value=false_value,
        label=_HAND_DETECTION[1],
        description=_HAND_DETECTION[2],
        device_kind=(_DK.keyboard, )
    )


def _register_fn_swap(register=_R.keyboard_fn_swap, true_value=b'\x00\x01', mask=b'\x00\x01'):
    return register_toggle(
        _FN_SWAP[0],
        register,
        true_value=true_value,
        mask=mask,
        label=_FN_SWAP[1],
        description=_FN_SWAP[2],
        device_kind=(_DK.keyboard, )
    )


def _register_smooth_scroll(register=_R.mouse_button_flags, true_value=0x40, mask=0x40):
    return register_toggle(
        _SMOOTH_SCROLL[0],
        register,
        true_value=true_value,
        mask=mask,
        label=_SMOOTH_SCROLL[1],
        description=_SMOOTH_SCROLL[2],
        device_kind=(_DK.mouse, _DK.trackball)
    )


def _register_side_scroll(register=_R.mouse_button_flags, true_value=0x02, mask=0x02):
    return register_toggle(
        _SIDE_SCROLL[0],
        register,
        true_value=true_value,
        mask=mask,
        label=_SIDE_SCROLL[1],
        description=_SIDE_SCROLL[2],
        device_kind=(_DK.mouse, _DK.trackball)
    )


def _register_dpi(register=_R.mouse_dpi, choices=None):
    return register_choices(
        _DPI[0], register, choices, label=_DPI[1], description=_DPI[2], device_kind=(_DK.mouse, _DK.trackball)
    )


def _feature_fn_swap():
    return feature_toggle(
        _FN_SWAP[0], _F.FN_INVERSION, label=_FN_SWAP[1], description=_FN_SWAP[2], device_kind=(_DK.keyboard, )
    )


# this might not be correct for this feature
def _feature_new_fn_swap():
    return feature_toggle(
        _FN_SWAP[0], _F.NEW_FN_INVERSION, label=_FN_SWAP[1], description=_FN_SWAP[2], device_kind=(_DK.keyboard, )
    )


# ignore the capabilities part of the feature - all devices should be able to swap Fn state
# just use the current host (first byte = 0xFF) part of the feature to read and set the Fn state
def _feature_k375s_fn_swap():
    return feature_toggle(
        _FN_SWAP[0],
        _F.K375S_FN_INVERSION,
        label=_FN_SWAP[1],
        description=_FN_SWAP[2],
        true_value=b'\xFF\x01',
        false_value=b'\xFF\x00',
        device_kind=(_DK.keyboard, )
    )


# FIXME: This will enable all supported backlight settings,
# we should allow the users to select which settings they want to enable.
def _feature_backlight2():
    return feature_toggle(
        _BACKLIGHT[0], _F.BACKLIGHT2, label=_BACKLIGHT[1], description=_BACKLIGHT[2], device_kind=(_DK.keyboard, )
    )


def _feature_hi_res_scroll():
    return feature_toggle(
        _HI_RES_SCROLL[0],
        _F.HI_RES_SCROLLING,
        label=_HI_RES_SCROLL[1],
        description=_HI_RES_SCROLL[2],
        device_kind=(_DK.mouse, _DK.trackball)
    )


def _feature_lowres_smooth_scroll():
    return feature_toggle(
        _LOW_RES_SCROLL[0],
        _F.LOWRES_WHEEL,
        label=_LOW_RES_SCROLL[1],
        description=_LOW_RES_SCROLL[2],
        device_kind=(_DK.mouse, _DK.trackball)
    )


def _feature_hires_smooth_invert():
    return feature_toggle(
        _HIRES_INV[0],
        _F.HIRES_WHEEL,
        read_fnid=0x10,
        write_fnid=0x20,
        true_value=0x04,
        mask=0x04,
        label=_HIRES_INV[1],
        description=_HIRES_INV[2],
        device_kind=(_DK.mouse, _DK.trackball)
    )


def _feature_hires_smooth_resolution():
    return feature_toggle(
        _HIRES_RES[0],
        _F.HIRES_WHEEL,
        read_fnid=0x10,
        write_fnid=0x20,
        true_value=0x02,
        mask=0x02,
        label=_HIRES_RES[1],
        description=_HIRES_RES[2],
        device_kind=(_DK.mouse, _DK.trackball)
    )


def _feature_smart_shift():
    _MIN_SMART_SHIFT_VALUE = 0
    _MAX_SMART_SHIFT_VALUE = 50

    class _SmartShiftRW(_FeatureRW):
        def __init__(self, feature):
            super(_SmartShiftRW, self).__init__(feature)

        def read(self, device):
            value = super(_SmartShiftRW, self).read(device)
            if _bytes2int(value[0:1]) == 1:
                # Mode = Freespin, map to minimum
                return _int2bytes(_MIN_SMART_SHIFT_VALUE, count=1)
            else:
                # Mode = smart shift, map to the value, capped at maximum
                threshold = min(_bytes2int(value[1:2]), _MAX_SMART_SHIFT_VALUE)
                return _int2bytes(threshold, count=1)

        def write(self, device, data_bytes):
            threshold = _bytes2int(data_bytes)
            # Freespin at minimum
            mode = 1 if threshold == _MIN_SMART_SHIFT_VALUE else 2

            # Ratchet at maximum
            if threshold == _MAX_SMART_SHIFT_VALUE:
                threshold = 255

            data = _int2bytes(mode, count=1) + _int2bytes(threshold, count=1) * 2
            return super(_SmartShiftRW, self).write(device, data)

    return feature_range(
        _SMART_SHIFT[0],
        _F.SMART_SHIFT,
        _MIN_SMART_SHIFT_VALUE,
        _MAX_SMART_SHIFT_VALUE,
        bytes_count=1,
        rw=_SmartShiftRW(_F.SMART_SHIFT),
        label=_SMART_SHIFT[1],
        description=_SMART_SHIFT[2],
        device_kind=(_DK.mouse, _DK.trackball)
    )


def _feature_adjustable_dpi_choices(device):
    # [1] getSensorDpiList(sensorIdx)
    reply = device.feature_request(_F.ADJUSTABLE_DPI, 0x10)
    # Should not happen, but might happen when the user unplugs device while the
    # query is being executed. TODO retry logic?
    assert reply, 'Oops, DPI list cannot be retrieved!'
    dpi_list = []
    step = None
    for val in _unpack('!7H', reply[1:1 + 14]):
        if val == 0:
            break
        if val >> 13 == 0b111:
            assert step is None and len(dpi_list) == 1, \
              'Invalid DPI list item: %r' % val
            step = val & 0x1fff
        else:
            dpi_list.append(val)
    if step:
        assert len(dpi_list) == 2, 'Invalid DPI list range: %r' % dpi_list
        dpi_list = range(dpi_list[0], dpi_list[1] + 1, step)
    return _NamedInts.list(dpi_list)


def _feature_adjustable_dpi():
    """Pointer Speed feature"""
    # Assume sensorIdx 0 (there is only one sensor)
    # [2] getSensorDpi(sensorIdx) -> sensorIdx, dpiMSB, dpiLSB
    # [3] setSensorDpi(sensorIdx, dpi)
    return feature_choices_dynamic(
        _DPI[0],
        _F.ADJUSTABLE_DPI,
        _feature_adjustable_dpi_choices,
        read_fnid=0x20,
        write_fnid=0x30,
        bytes_count=3,
        label=_DPI[1],
        description=_DPI[2],
        device_kind=(_DK.mouse, _DK.trackball)
    )


def _feature_pointer_speed():
    """Pointer Speed feature"""
    # min and max values taken from usb traces of Win software
    return feature_range(
        _POINTER_SPEED[0],
        _F.POINTER_SPEED,
        0x002e,
        0x01ff,
        read_fnid=0x0,
        write_fnid=0x10,
        bytes_count=2,
        label=_POINTER_SPEED[1],
        description=_POINTER_SPEED[2],
        device_kind=(_DK.mouse, _DK.trackball)
    )


# the keys for the choice map are Logitech controls (from special_keys)
# each choice value is a NamedInt with the string from a task (to be shown to the user)
# and the integer being the control number for that task (to be written to the device)
# Solaar only remaps keys (controlled by key gmask and group), not other key reprogramming
def _feature_reprogrammable_keys_choices(device):
    count = device.feature_request(_F.REPROG_CONTROLS_V4)
    assert count, 'Oops, reprogrammable key count cannot be retrieved!'
    count = ord(count[:1])  # the number of key records
    keys = [None] * count
    groups = [[] for i in range(0, 9)]
    choices = {}
    for i in range(0, count):  # get the data for each key record on device
        keydata = device.feature_request(_F.REPROG_CONTROLS_V4, 0x10, i)
        key, key_task, flags, pos, group, gmask = _unpack('!HHBBBB', keydata[:8])
        action = _NamedInt(key, str(_special_keys.TASK[key_task]))
        keys[i] = (_special_keys.CONTROL[key], action, flags, gmask)
        groups[group].append(action)
    for k in keys:
        # if k[2] & _special_keys.KEY_FLAG.reprogrammable:  # this flag is only to show in UI, ignore in Solaar
        if k[3]:  # only keys with a non-zero gmask are remappable
            key_choices = [k[1]]  # it should always be possible to map the key to itself
            for g in range(1, 9):  # group 0 and gmask 0 (k[3]) does not indicate remappability so don't consider group 0
                if (k[3] == 0 if g == 0 else k[3] & 2**(g - 1)):
                    for gm in groups[g]:
                        if int(gm) != int(k[0]):  # don't put itself in twice
                            key_choices.append(gm)
            if len(key_choices) > 1:
                choices[k[0]] = key_choices
    return choices


def _feature_reprogrammable_keys():
    return feature_map_choices_dynamic(
        _REPROGRAMMABLE_KEYS[0],
        _F.REPROG_CONTROLS_V4,
        _feature_reprogrammable_keys_choices,
        read_fnid=0x20,
        write_fnid=0x30,
        key_bytes_count=2,
        bytes_count=2,
        read_skip_bytes_count=1,
        write_prefix_bytes=b'\x00',
        extra_default=0,
        label=_REPROGRAMMABLE_KEYS[1],
        description=_REPROGRAMMABLE_KEYS[2],
        device_kind=(_DK.keyboard, ),
    )


def _feature_disable_keyboard_keys_key_list(device):
    mask = device.feature_request(_F.KEYBOARD_DISABLE_KEYS)[0]
    options = [_special_keys.DISABLE[1 << i] for i in range(8) if mask & (1 << i)]
    return options


def _feature_disable_keyboard_keys():
    return feature_bitfield_toggle_dynamic(
        _DISABLE_KEYS[0],
        _F.KEYBOARD_DISABLE_KEYS,
        _feature_disable_keyboard_keys_key_list,
        read_fnid=0x10,
        write_fnid=0x20,
        label=_DISABLE_KEYS[1],
        description=_DISABLE_KEYS[2],
        device_kind=(_DK.keyboard, )
    )


# muultiplatform OS bits
OSS = [('Linux', 0x0400), ('MacOS', 0x2000), ('Windows', 0x0100), ('iOS', 0x4000), ('Android', 0x1000), ('WebOS', 0x8000),
       ('Chrome', 0x0800), ('WinEmb', 0x0200), ('Tizen', 0x0001)]


def _feature_multiplatform_choices(device):
    def _str_os_versions(low, high):
        def _str_os_version(version):
            if version == 0:
                return ''
            elif version & 0xFF:
                return str(version >> 8) + '.' + str(version & 0xFF)
            else:
                return str(version >> 8)

        return '' if low == 0 and high == 0 else ' ' + _str_os_version(low) + '-' + _str_os_version(high)

    infos = device.feature_request(_F.MULTIPLATFORM)
    assert infos, 'Oops, multiplatform count cannot be retrieved!'
    flags, _ignore, num_descriptors = _unpack('!BBB', infos[:3])
    if not (flags & 0x02):  # can't set platform so don't create setting
        return []
    descriptors = []
    for index in range(0, num_descriptors):
        descriptor = device.feature_request(_F.MULTIPLATFORM, 0x10, index)
        platform, _ignore, os_flags, low, high = _unpack('!BBHHH', descriptor[:8])
        descriptors.append((platform, os_flags, low, high))
    choices = _NamedInts()
    for os_name, os_bit in OSS:
        for platform, os_flags, low, high in descriptors:
            os = os_name + _str_os_versions(low, high)
            if os_bit & os_flags and platform not in choices and os not in choices:
                choices[platform] = os
    return choices


def _feature_multiplatform():
    return feature_choices_dynamic(
        _PLATFORM[0],
        _F.MULTIPLATFORM,
        _feature_multiplatform_choices,
        read_fnid=0x00,
        read_skip_bytes_count=6,
        write_fnid=0x30,
        write_prefix_bytes=b'\xff',
        label=_PLATFORM[1],
        description=_PLATFORM[2]
    )


PLATFORMS = _NamedInts()
PLATFORMS[0x00] = 'iOS, MacOS'
PLATFORMS[0x01] = 'Android, Windows'


def _feature_dualplatform():
    return feature_choices(
        _PLATFORM[0],
        _F.DUALPLATFORM,
        PLATFORMS,
        read_fnid=0x10,
        write_fnid=0x20,
        label=_PLATFORM[1],
        description=_PLATFORM[2],
        device_kind=(_DK.keyboard, )
    )


def _feature_change_host_choices(device):
    infos = device.feature_request(_F.CHANGE_HOST)
    assert infos, 'Oops, host count cannot be retrieved!'
    numHosts, currentHost = _unpack('!BB', infos[:2])
    hostNames = _hidpp20.get_host_names(device)
    hostNames = hostNames if hostNames is not None else {}
    if currentHost not in hostNames or hostNames[currentHost][1] == '':
        import socket  # find name of current host and use it
        hostNames[currentHost] = (True, socket.gethostname().partition('.')[0])
    choices = _NamedInts()
    for host in range(0, numHosts):
        _ignore, hostName = hostNames.get(host, (False, ''))
        choices[host] = str(host + 1) + ':' + hostName if hostName else str(host + 1)
    return choices


def _feature_change_host():
    return feature_choices_dynamic(
        _CHANGE_HOST[0],
        _F.CHANGE_HOST,
        _feature_change_host_choices,
        persist=False,
        no_reply=True,
        read_fnid=0x00,
        read_skip_bytes_count=1,
        write_fnid=0x10,
        label=_CHANGE_HOST[1],
        description=_CHANGE_HOST[2]
    )


def _feature_thumb_mode():
    return feature_toggle(
        _THUMB_SCROLL_MODE[0],
        _F.THUMB_WHEEL,
        read_fnid=0x10,
        write_fnid=0x20,
        true_value=b'\x01\x00',
        false_value=b'\x00\x00',
        mask=b'\x01\x00',
        label=_THUMB_SCROLL_MODE[1],
        description=_THUMB_SCROLL_MODE[2],
        device_kind=(_DK.mouse, _DK.trackball)
    )


def _feature_thumb_invert():
    return feature_toggle(
        _THUMB_SCROLL_INVERT[0],
        _F.THUMB_WHEEL,
        read_fnid=0x10,
        write_fnid=0x20,
        true_value=b'\x00\x01',
        false_value=b'\x00\x00',
        mask=b'\x00\x01',
        label=_THUMB_SCROLL_INVERT[1],
        description=_THUMB_SCROLL_INVERT[2],
        device_kind=(_DK.mouse, _DK.trackball)
    )


#
#
#


def _S(name, featureID=None, featureFn=None, registerFn=None, identifier=None):
    return (name, featureID, featureFn, registerFn, identifier if identifier else name.replace('-', '_'))


_SETTINGS_TABLE = [
    _S(_HAND_DETECTION[0], registerFn=_register_hand_detection),
    _S(_SMOOTH_SCROLL[0], registerFn=_register_smooth_scroll),
    _S(_SIDE_SCROLL[0], registerFn=_register_side_scroll),
    _S(_HI_RES_SCROLL[0], _F.HI_RES_SCROLLING, _feature_hi_res_scroll),
    _S(_LOW_RES_SCROLL[0], _F.LOWRES_WHEEL, _feature_lowres_smooth_scroll),
    _S(_HIRES_INV[0], _F.HIRES_WHEEL, _feature_hires_smooth_invert),
    _S(_HIRES_RES[0], _F.HIRES_WHEEL, _feature_hires_smooth_resolution),
    _S(_FN_SWAP[0], _F.FN_INVERSION, _feature_fn_swap, registerFn=_register_fn_swap),
    _S(_FN_SWAP[0], _F.NEW_FN_INVERSION, _feature_new_fn_swap, identifier='new_fn_swap'),
    _S(_FN_SWAP[0], _F.K375S_FN_INVERSION, _feature_k375s_fn_swap, identifier='k375s_fn_swap'),
    _S(_DPI[0], _F.ADJUSTABLE_DPI, _feature_adjustable_dpi, registerFn=_register_dpi),
    _S(_POINTER_SPEED[0], _F.POINTER_SPEED, _feature_pointer_speed),
    _S(_SMART_SHIFT[0], _F.SMART_SHIFT, _feature_smart_shift),
    _S(_BACKLIGHT[0], _F.BACKLIGHT2, _feature_backlight2),
    _S(_REPROGRAMMABLE_KEYS[0], _F.REPROG_CONTROLS_V4, _feature_reprogrammable_keys),
    _S(_DISABLE_KEYS[0], _F.KEYBOARD_DISABLE_KEYS, _feature_disable_keyboard_keys),
    _S(_PLATFORM[0], _F.MULTIPLATFORM, _feature_multiplatform),
    _S(_PLATFORM[0], _F.DUALPLATFORM, _feature_dualplatform, identifier='dualplatform'),
    _S(_CHANGE_HOST[0], _F.CHANGE_HOST, _feature_change_host),
    _S(_THUMB_SCROLL_MODE[0], _F.THUMB_WHEEL, _feature_thumb_mode),
    _S(_THUMB_SCROLL_INVERT[0], _F.THUMB_WHEEL, _feature_thumb_invert),
]

_SETTINGS_LIST = namedtuple('_SETTINGS_LIST', [s[4] for s in _SETTINGS_TABLE])
RegisterSettings = _SETTINGS_LIST._make([s[3] for s in _SETTINGS_TABLE])
FeatureSettings = _SETTINGS_LIST._make([s[2] for s in _SETTINGS_TABLE])

del _SETTINGS_LIST

#
#
#


def check_feature(device, name, featureId, featureFn):
    """
    :param name: name for the setting
    :param featureId: the numeric Feature ID for this setting implementation
    :param featureFn: the function for this setting implementation
    """
    if featureId not in device.features:
        return
    try:
        detected = featureFn()(device)
        if _log.isEnabledFor(_DEBUG):
            _log.debug('check_feature[%s] detected %s', featureId, detected)
        return detected
    except Exception:
        from traceback import format_exc
        _log.error('check_feature[%s] inconsistent feature %s', featureId, format_exc())


# Returns True if device was queried to find features, False otherwise
def check_feature_settings(device, already_known):
    """Try to auto-detect device settings by the HID++ 2.0 features they have."""
    if device.features is None or not device.online:
        return False
    if device.protocol and device.protocol < 2.0:
        return False
    for name, featureId, featureFn, __, __ in _SETTINGS_TABLE:
        if featureId and featureFn:
            if not any(s.name == name for s in already_known):
                setting = check_feature(device, name, featureId, featureFn)
                if setting:
                    already_known.append(setting)
    return True


def check_feature_setting(device, setting_name):
    for name, featureId, featureFn, __, __ in _SETTINGS_TABLE:
        if name == setting_name and featureId and featureFn:
            return check_feature(device, name, featureId, featureFn)
