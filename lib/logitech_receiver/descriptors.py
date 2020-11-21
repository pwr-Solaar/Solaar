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

from .common import NamedInts as _NamedInts
from .hidpp10 import DEVICE_KIND as _DK
from .hidpp10 import REGISTERS as _R
from .settings_templates import FeatureSettings as _FS
from .settings_templates import RegisterSettings as _RS

#
#
#

_DeviceDescriptor = namedtuple(
    '_DeviceDescriptor',
    ('name', 'kind', 'wpid', 'codename', 'protocol', 'registers', 'settings', 'persister', 'usbid', 'interface', 'btid')
)
del namedtuple

DEVICES_WPID = {}
DEVICES = {}


def _D(
    name,
    codename=None,
    kind=None,
    wpid=None,
    protocol=None,
    registers=None,
    settings=None,
    persister=None,
    usbid=None,
    interface=None,
    btid=None,
):
    assert name

    if kind is None:
        kind = (
            _DK.mouse if 'Mouse' in name else _DK.keyboard if 'Keyboard' in name else _DK.numpad
            if 'Number Pad' in name else _DK.touchpad if 'Touchpad' in name else _DK.trackball if 'Trackball' in name else None
        )
    assert kind is not None, 'descriptor for %s does not have kind set' % name

    # heuristic: the codename is the last word in the device name
    if codename is None and ' ' in name:
        codename = name.split(' ')[-1]
    assert codename is not None, 'descriptor for %s does not have codename set' % name

    if protocol is not None:
        # ? 2.0 devices should not have any registers
        _kind = lambda s: s._rw.kind if hasattr(s, '_rw') else s._rw_kind
        if protocol < 2.0:
            assert settings is None or all(_kind(s) == 1 for s in settings)
        else:
            assert registers is None
            assert settings is None or all(_kind(s) == 2 for s in settings)

        if wpid:
            for w in wpid if isinstance(wpid, tuple) else (wpid, ):
                if protocol > 1.0:
                    assert w[0:1] == '4', '%s has protocol %0.1f, wpid %s' % (name, protocol, w)
                else:
                    if w[0:1] == '1':
                        assert kind == _DK.mouse, '%s has protocol %0.1f, wpid %s' % (name, protocol, w)
                    elif w[0:1] == '2':
                        assert kind in (_DK.keyboard, _DK.numpad), '%s has protocol %0.1f, wpid %s' % (name, protocol, w)

    device_descriptor = _DeviceDescriptor(
        name=name,
        kind=kind,
        wpid=wpid,
        codename=codename,
        protocol=protocol,
        registers=registers,
        settings=settings,
        persister=persister,
        usbid=usbid,
        interface=interface,
        btid=btid
    )

    if usbid:
        found = get_usbid(usbid)
        assert found is None, 'duplicate usbid in device descriptors: %s' % (found, )
    if btid:
        found = get_btid(btid)
        assert found is None, 'duplicate btid in device descriptors: %s' % (found, )

    assert codename not in DEVICES, 'duplicate codename in device descriptors: %s' % (DEVICES[codename], )
    DEVICES[codename] = device_descriptor

    if wpid:
        for w in wpid if isinstance(wpid, tuple) else (wpid, ):
            assert w not in DEVICES_WPID, 'duplicate wpid in device descriptors: %s' % (DEVICES_WPID[w], )
            DEVICES_WPID[w] = device_descriptor


def get_wpid(wpid):
    return DEVICES_WPID.get(wpid)


def get_codename(codename):
    return DEVICES.get(codename)


def get_usbid(usbid):
    if isinstance(usbid, str):
        usbid = int(usbid, 16)
    found = next((x for x in DEVICES.values() if x.usbid == usbid), None)
    return found


def get_btid(btid):
    if isinstance(btid, str):
        btid = int(btid, 16)
    found = next((x for x in DEVICES.values() if x.btid == btid), None)
    return found


#
#
#

_PERFORMANCE_MX_DPIS = _NamedInts.range(0x81, 0x8F, lambda x: str((x - 0x80) * 100))

#
#
#

# Some HID++1.0 registers and HID++2.0 features can be discovered at run-time,
# so they are not specified here.
#
# For known registers, however, please do specify them here -- avoids
# unnecessary communication with the device and makes it easier to make certain
# decisions when querying the device's state.
#
# Specify a negative value to blacklist a certain register for a device.
#
# Usually, state registers (battery, leds, some features, etc) are only used by
# HID++ 1.0 devices, while HID++ 2.0 devices use features for the same
# functionalities. This is a rule that's been discovered by trial-and-error,
# so it may change in the future.

# Well-known registers (in hex):
#  * 00 - notification flags (all devices)
#    01 - mice: smooth scrolling
#    07 - battery status
#    09 - keyboards: FN swap (if it has the FN key)
#    0D - battery charge
#       a device may have either the 07 or 0D register available;
#       no known device uses both
#    51 - leds
#    63 - mice: DPI
#  * F1 - firmware info
# Some registers appear to be universally supported, no matter the HID++ version
# (marked with *). The rest may or may not be supported, and their values may or
# may not mean the same thing across different devices.

# The 'codename' and 'kind' fields are usually guessed from the device name,
# but in some cases (like the Logitech Cube) that heuristic fails and they have
# to be specified.
#
# The 'protocol' and 'wpid' fields are optional (they can be discovered at
# runtime), but specifying them here speeds up device discovery and reduces the
# USB traffic Solaar has to do to fully identify peripherals.
# Same goes for HID++ 2.0 feature settings (like _feature_fn_swap).
#
# The 'registers' field indicates read-only registers, specifying a state. These
# are valid (AFAIK) only to HID++ 1.0 devices.
# The 'settings' field indicates a read/write register; based on them Solaar
# generates, at runtime, the settings controls in the device panel. HID++ 1.0
# devices may only have register-based settings; HID++ 2.0 devices may only have
# feature-based settings.

# Keyboards

_D('Wireless Keyboard K230', protocol=2.0, wpid='400D')
_D('Wireless Keyboard K270(unifying)', protocol=2.0, wpid='4003')
_D(
    'Wireless Keyboard MK270',
    protocol=2.0,
    wpid='4023',
    settings=[_FS.fn_swap()],
)
_D(
    'Wireless Keyboard K270',
    protocol=1.0,
    registers=(_R.battery_status, ),
)
_D(
    'Wireless Keyboard MK300',
    protocol=1.0,
    wpid='0068',
    registers=(_R.battery_status, ),
)

_D(
    'Wireless Keyboard MK320',
    protocol=1.0,
    wpid='200F',
    registers=(_R.battery_status, ),
)
_D('Wireless Keyboard MK330')
_D(
    'Wireless Compact Keyboard K340',
    protocol=1.0,
    wpid='2007',
    registers=(_R.battery_status, ),
)
_D(
    'Wireless Wave Keyboard K350',
    protocol=1.0,
    wpid='200A',
    registers=(_R.battery_status, ),
)
_D(
    'Wireless Keyboard K360',
    protocol=2.0,
    wpid='4004',
    settings=[_FS.fn_swap()],
)
_D(
    'Wireless Keyboard K375s',
    protocol=2.0,
    wpid='4061',
    settings=[_FS.k375s_fn_swap()],
)
_D(
    'Wireless Touch Keyboard K400',
    protocol=2.0,
    wpid=('400E', '4024'),
    settings=[_FS.fn_swap()],
)
_D(
    'Wireless Touch Keyboard K400 Plus',
    codename='K400 Plus',
    protocol=2.0,
    wpid='404D',
    settings=[
        _FS.new_fn_swap(),
        _FS.reprogrammable_keys(),
        _FS.disable_keyboard_keys(),
        _FS.gesture2_gestures(),
        _FS.gesture2_params(),
    ],
)
_D(
    'Wireless Keyboard K520',
    protocol=1.0,
    wpid='2011',
    registers=(_R.battery_status, ),
    settings=[
        _RS.fn_swap(),
    ],
)
_D(
    'Number Pad N545',
    protocol=1.0,
    wpid='2006',
    registers=(_R.battery_status, ),
)
_D('Wireless Keyboard MK550')
_D(
    'Wireless Keyboard MK700',
    protocol=1.0,
    wpid='2008',
    registers=(_R.battery_status, ),
    settings=[
        _RS.fn_swap(),
    ],
)
_D(
    'Wireless Solar Keyboard K750',
    protocol=2.0,
    wpid='4002',
    settings=[_FS.fn_swap()],
)
_D(
    'Wireless Multi-Device Keyboard K780',
    protocol=4.5,
    wpid='405B',
    settings=[_FS.new_fn_swap()],
)
_D(
    'Wireless Illuminated Keyboard K800',
    protocol=1.0,
    wpid='2010',
    registers=(
        _R.battery_status,
        _R.three_leds,
    ),
    settings=[
        _RS.fn_swap(),
        _RS.hand_detection(),
    ],
)
_D(
    'Wireless Illuminated Keyboard K800 new',
    codename='K800 new',
    protocol=4.5,
    wpid='406E',
    settings=[_FS.fn_swap()],
)
_D(
    'Illuminated Living-Room Keyboard K830',
    protocol=2.0,
    wpid='4032',
    settings=[_FS.new_fn_swap()],
)
_D('Craft Advanced Keyboard', codename='Craft', protocol=4.5, wpid='4066', btid=0xB350)
_D('MX Keys Keyboard', codename='MX Keys', protocol=4.5, wpid='408A', btid=0xB35B)
_D(
    'Wireless Keyboard S510',
    codename='S510',
    protocol=1.0,
    wpid='0056',
    registers=(_R.battery_status, ),
)
_D(
    'Wireless Keyboard EX100',
    codename='EX100',
    protocol=1.0,
    wpid='0065',
    registers=(_R.battery_status, ),
)

# Mice

_D('Wireless Mouse M150', protocol=2.0, wpid='4022')
_D('Wireless Mouse M175', protocol=2.0, wpid='4008')
_D(
    'Wireless Mouse M185 new',
    codename='M185n',
    protocol=4.5,
    wpid='4054',
    settings=[
        _FS.lowres_smooth_scroll(),
        _FS.pointer_speed(),
    ]
)
# Apparently Logitech uses wpid 4055 for three different mice
# That's not so strange, as M185 is used on both Unifying-ready and non-Unifying-ready mice
_D(
    'Wireless Mouse M185/M235/M310',
    codename='M185/M235/M310',
    protocol=4.5,
    wpid='4055',
    settings=[
        _FS.lowres_smooth_scroll(),
        _FS.pointer_speed(),
    ]
)
_D('Wireless Mouse M185', protocol=2.0, wpid='4038')
_D('Wireless Mouse M187', protocol=2.0, wpid='4019')
_D('Wireless Mouse M215', protocol=1.0, wpid='1020')
_D(
    'Wireless Mouse M305',
    protocol=1.0,
    wpid='101F',
    registers=(_R.battery_status, ),
    settings=[
        _RS.side_scroll(),
    ],
)
_D(
    'Wireless Mouse M310',
    protocol=1.0,
    wpid='1024',
    registers=(_R.battery_status, ),
)
_D('Wireless Mouse M315')
_D('Wireless Mouse M317')
_D('Wireless Mouse M325', protocol=2.0, wpid='400A', settings=[
    _FS.hi_res_scroll(),
])
_D('Wireless Mouse M345', protocol=2.0, wpid='4017')
_D(
    'Wireless Mouse M350',
    protocol=1.0,
    wpid='101C',
    registers=(_R.battery_charge, ),
)
_D('Wireless Mouse Pebble M350', codename='Pebble', protocol=2.0, wpid='4080')
_D(
    'Wireless Mouse M505',
    codename='M505/B605',
    protocol=1.0,
    wpid='101D',
    registers=(_R.battery_charge, ),
    settings=[
        _RS.smooth_scroll(),
        _RS.side_scroll(),
    ],
)
_D(
    'Wireless Mouse M510',
    protocol=1.0,
    wpid='1025',
    registers=(_R.battery_status, ),
    settings=[
        # _RS.smooth_scroll(),	# writing the bit to the register doesn't cause an error, but the bit doesn't turn on
        _RS.side_scroll(),
    ],
)
_D('Wireless Mouse M510', codename='M510v2', protocol=2.0, wpid='4051', settings=[
    _FS.lowres_smooth_scroll(),
])
_D('Couch Mouse M515', protocol=2.0, wpid='4007')
_D('Wireless Mouse M525', protocol=2.0, wpid='4013')
_D(
    'Multi Device Silent Mouse M585/M590',
    codename='M585/M590',
    protocol=4.5,
    wpid='406B',
    settings=[
        _FS.lowres_smooth_scroll(),
        _FS.pointer_speed(),
    ],
)
_D('Touch Mouse M600', protocol=2.0, wpid='401A')
_D(
    'Marathon Mouse M705 (M-R0009)',
    codename='M705 (M-R0009)',
    protocol=1.0,
    wpid='101B',
    registers=(_R.battery_charge, ),
    settings=[
        _RS.smooth_scroll(),
        _RS.side_scroll(),
    ],
)
_D(
    'Marathon Mouse M705 (M-R0073)',
    codename='M705 (M-R0073)',
    protocol=4.5,
    wpid='406D',
    settings=[
        _FS.hires_smooth_invert(),
        _FS.hires_smooth_resolution(),
        _FS.pointer_speed(),
    ]
)
_D('Zone Touch Mouse T400')
_D('Touch Mouse T620', protocol=2.0)
_D('Logitech Cube', kind=_DK.mouse, protocol=2.0)
_D(
    'Anywhere Mouse MX',
    codename='Anywhere MX',
    protocol=1.0,
    wpid='1017',
    registers=(_R.battery_charge, ),
    settings=[
        _RS.smooth_scroll(),
        _RS.side_scroll(),
    ],
)
_D(
    'Anywhere Mouse MX 2',
    codename='Anywhere MX 2',
    protocol=4.5,
    wpid='404A',
    settings=[
        _FS.hires_smooth_invert(),
        _FS.hires_smooth_resolution(),
    ],
)
_D(
    'Performance Mouse MX',
    codename='Performance MX',
    protocol=1.0,
    wpid='101A',
    registers=(
        _R.battery_status,
        _R.three_leds,
    ),
    settings=[
        _RS.dpi(choices=_PERFORMANCE_MX_DPIS),
        _RS.smooth_scroll(),
        _RS.side_scroll(),
    ],
)

_D(
    'Wireless Mouse MX Master',
    codename='MX Master',
    protocol=4.5,
    wpid='4041',
    btid=0xb012,
    settings=[
        _FS.hires_smooth_invert(),
        _FS.hires_smooth_resolution(),
    ],
)

_D(
    'Wireless Mouse MX Master 2S',
    codename='MX Master 2S',
    protocol=4.5,
    wpid='4069',
    btid=0xb019,
    settings=[
        _FS.hires_smooth_invert(),
        _FS.hires_smooth_resolution(),
        _FS.gesture2_gestures(),
    ],
)

_D('MX Master 3 Wireless Mouse', codename='MX Master 3', protocol=4.5, wpid='4082', btid=0xb023)

_D('MX Vertical Wireless Mouse', codename='MX Vertical', protocol=4.5, wpid='407B', btid=0xb020, usbid=0xc08a)

_D(
    'G7 Cordless Laser Mouse',
    codename='G7',
    protocol=1.0,
    wpid='1002',
    registers=(_R.battery_status, ),
)
_D(
    'G700 Gaming Mouse',
    codename='G700',
    protocol=1.0,
    wpid='1023',
    registers=(
        _R.battery_status,
        _R.three_leds,
    ),
    settings=[
        _RS.smooth_scroll(),
        _RS.side_scroll(),
    ],
)
_D(
    'G700s Gaming Mouse',
    codename='G700s',
    protocol=1.0,
    wpid='102A',
    usbid=0xc07c,
    interface=1,
    registers=(
        _R.battery_status,
        _R.three_leds,
    ),
    settings=[
        _RS.smooth_scroll(),
        _RS.side_scroll(),
    ],
)

_D('G403 Gaming Mouse', codename='G403', usbid=0xc082)
_D('G502 Hero Gaming Mouse', codename='G502 Hero', usbid=0xc08d)
_D('G703 Lightspeed Gaming Mouse', codename='G703', usbid=0xc087)
_D('G703 Hero Gaming Mouse', codename='G703 Hero', usbid=0xc090)
_D('G900 Chaos Spectrum Gaming Mouse', codename='G900', usbid=0xc081)
_D('G903 Lightspeed Gaming Mouse', codename='G903', usbid=0xc086)
_D('G903 Hero Gaming Mouse', codename='G903 Hero', usbid=0xc091)
_D('GPro Gaming Mouse', codename='GPro', usbid=0xc088)

_D(
    'LX5 Cordless Mouse',
    codename='LX5',
    protocol=1.0,
    wpid='0036',
    registers=(_R.battery_status, ),
)
_D(
    'Wireless Mouse M30',
    codename='M30',
    protocol=1.0,
    wpid='0085',
    registers=(_R.battery_status, ),
)
_D(
    'Wireless Mouse EX100',
    codename='EX100m',
    protocol=1.0,
    wpid='003F',
    registers=(_R.battery_status, ),
    # settings=[ _RS.smooth_scroll(), ], # command accepted, but no change in whell action
)

# Trackballs

_D('Wireless Trackball M570')

# Touchpads

_D('Wireless Rechargeable Touchpad T650', protocol=2.0, wpid='4101')
_D('Wireless Touchpad', codename='Wireless Touch', protocol=2.0, wpid='4011')

#
# Classic Nano peripherals (that don't support the Unifying protocol).
# A wpid is necessary to properly identify them.
#

_D(
    'VX Nano Cordless Laser Mouse',
    codename='VX Nano',
    protocol=1.0,
    wpid=('100B', '100F'),
    registers=(_R.battery_charge, ),
    settings=[
        _RS.smooth_scroll(),
        _RS.side_scroll(),
    ],
)
_D(
    'V450 Nano Cordless Laser Mouse',
    codename='V450 Nano',
    protocol=1.0,
    wpid='1011',
    registers=(_R.battery_charge, ),
)
_D(
    'V550 Nano Cordless Laser Mouse',
    codename='V550 Nano',
    protocol=1.0,
    wpid='1013',
    registers=(_R.battery_charge, ),
    settings=[
        _RS.smooth_scroll(),
        _RS.side_scroll(),
    ],
)

# Mini receiver mice

_D(
    'MX610 Laser Cordless Mouse',
    codename='MX610',
    protocol=1.0,
    wpid='1001',
    registers=(_R.battery_status, ),
)
_D(
    'MX620 Laser Cordless Mouse',
    codename='MX620',
    protocol=1.0,
    wpid=('100A', '1016'),
    registers=(_R.battery_charge, ),
)
_D(
    'MX610 Left-Handled Mouse',
    codename='MX610L',
    protocol=1.0,
    wpid='1004',
    registers=(_R.battery_status, ),
)
_D(
    'V400 Laser Cordless Mouse',
    codename='V400',
    protocol=1.0,
    wpid='1003',
    registers=(_R.battery_status, ),
)
_D(
    'V450 Laser Cordless Mouse',
    codename='V450',
    protocol=1.0,
    wpid='1005',
    registers=(_R.battery_status, ),
)
_D(
    'VX Revolution',
    codename='VX Revolution',
    kind=_DK.mouse,
    protocol=1.0,
    wpid=('1006', '100D', '0612'),  # WPID 0612 from Issue #921
    registers=(_R.battery_charge, ),
)
_D(
    'MX Air',
    codename='MX Air',
    protocol=1.0,
    kind=_DK.mouse,
    wpid=('1007', '100E'),
    registers=(_R.battery_charge, ),
)
_D(
    'MX Revolution',
    codename='MX Revolution',
    protocol=1.0,
    kind=_DK.mouse,
    wpid=('1008', '100C'),
    registers=(_R.battery_charge, ),
)
_D(
    'MX 1100 Cordless Laser Mouse',
    codename='MX 1100',
    protocol=1.0,
    kind=_DK.mouse,
    wpid='1014',
    registers=(_R.battery_charge, ),
    settings=[
        _RS.smooth_scroll(),
        _RS.side_scroll(),
    ],
)

# Some exotics...

_D('Fujitsu Sonic Mouse', codename='Sonic', protocol=1.0, wpid='1029')
