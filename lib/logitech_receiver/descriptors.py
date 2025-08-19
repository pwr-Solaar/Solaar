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


"""Devices (not receivers) known to Solaar.

Solaar can handle many recent devices without having any entry here.
An entry should only be added to fix problems, such as
- the device's device ID or WPID falls outside the range that Solaar searches
- the device uses a USB interface other than 2
- the name or codename should be different from what the device reports
"""

from .hidpp10_constants import DEVICE_KIND
from .hidpp10_constants import Registers as Reg


class _DeviceDescriptor:
    def __init__(
        self,
        name=None,
        kind=None,
        wpid=None,
        codename=None,
        protocol=None,
        registers=None,
        usbid=None,
        interface=None,
        btid=None,
    ):
        self.name = name
        self.kind = kind
        self.wpid = wpid
        self.codename = codename
        self.protocol = protocol
        self.registers = registers
        self.usbid = usbid
        self.interface = interface
        self.btid = btid
        self.settings = None


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
    usbid=None,
    interface=None,
    btid=None,
):
    if kind is None:
        kind = (
            DEVICE_KIND.mouse
            if "Mouse" in name
            else DEVICE_KIND.keyboard
            if "Keyboard" in name
            else DEVICE_KIND.numpad
            if "Number Pad" in name
            else DEVICE_KIND.touchpad
            if "Touchpad" in name
            else DEVICE_KIND.trackball
            if "Trackball" in name
            else None
        )
    assert kind is not None, f"descriptor for {name} does not have kind set"

    if protocol is not None:
        if wpid:
            for w in wpid if isinstance(wpid, tuple) else (wpid,):
                if protocol > 1.0:
                    assert w[0:1] == "4", f"{name} has protocol {protocol:0.1f}, wpid {w}"
                else:
                    if w[0:1] == "1":
                        assert kind == DEVICE_KIND.mouse, f"{name} has protocol {protocol:0.1f}, wpid {w}"
                    elif w[0:1] == "2":
                        assert kind in (
                            DEVICE_KIND.keyboard,
                            DEVICE_KIND.numpad,
                        ), f"{name} has protocol {protocol:0.1f}, wpid {w}"

    device_descriptor = _DeviceDescriptor(
        name=name,
        kind=kind,
        wpid=wpid,
        codename=codename,
        protocol=protocol,
        registers=registers,
        usbid=usbid,
        interface=interface,
        btid=btid,
    )

    if usbid:
        found = get_usbid(usbid)
        assert found is None, f"duplicate usbid in device descriptors: {found}"
    if btid:
        found = get_btid(btid)
        assert found is None, f"duplicate btid in device descriptors: {found}"

    assert codename not in DEVICES, f"duplicate codename in device descriptors: {DEVICES[codename]}"
    if codename:
        DEVICES[codename] = device_descriptor

    if wpid:
        for w in wpid if isinstance(wpid, tuple) else (wpid,):
            assert w not in DEVICES_WPID, f"duplicate wpid in device descriptors: {DEVICES_WPID[w]}"
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


# Some HID++1.0 registers and HID++2.0 features can be discovered at run-time,
# so they are not specified here.
#
# State registers (battery, leds, some features, etc) are only used by
# HID++ 1.0 devices, while HID++ 2.0 devices use features for the same
# functionalities.

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
#
# The 'registers' field indicates read-only registers, specifying a state. These
# are valid (AFAIK) only to HID++ 1.0 devices.
# The 'settings' field indicates a read/write register; based on them Solaar
# generates, at runtime, the settings controls in the device panel.
# Solaar now sets up this field in settings_templates.py to eliminate a imports loop.
# HID++ 1.0 devices may only have register-based settings; HID++ 2.0 devices may only have
# feature-based settings.

# Devices are organized by kind
# Within kind devices are sorted by wpid, then by usbid, then by btid, with missing values sorted later

# Keyboards

_D("Wireless Keyboard EX110", codename="EX110", protocol=1.0, wpid="0055", registers=(Reg.BATTERY_STATUS,))
_D("Wireless Keyboard S510", codename="S510", protocol=1.0, wpid="0056", registers=(Reg.BATTERY_STATUS,))
_D("Wireless Wave Keyboard K550", codename="K550", protocol=1.0, wpid="0060", registers=(Reg.BATTERY_STATUS,))
_D("Wireless Keyboard EX100", codename="EX100", protocol=1.0, wpid="0065", registers=(Reg.BATTERY_STATUS,))
_D("Wireless Keyboard MK300", codename="MK300", protocol=1.0, wpid="0068", registers=(Reg.BATTERY_STATUS,))
_D("Number Pad N545", codename="N545", protocol=1.0, wpid="2006", registers=(Reg.BATTERY_STATUS,))
_D("Wireless Compact Keyboard K340", codename="K340", protocol=1.0, wpid="2007", registers=(Reg.BATTERY_STATUS,))
_D("Wireless Keyboard MK700", codename="MK700", protocol=1.0, wpid="2008", registers=(Reg.BATTERY_STATUS,))
_D("Wireless Wave Keyboard K350", codename="K350", protocol=1.0, wpid="200A", registers=(Reg.BATTERY_STATUS,))
_D("Wireless Keyboard MK320", codename="MK320", protocol=1.0, wpid="200F", registers=(Reg.BATTERY_STATUS,))
_D(
    "Wireless Illuminated Keyboard K800",
    codename="K800",
    protocol=1.0,
    wpid="2010",
    registers=(Reg.BATTERY_STATUS, Reg.THREE_LEDS),
)
_D("Wireless Keyboard K520", codename="K520", protocol=1.0, wpid="2011", registers=(Reg.BATTERY_STATUS,))
_D("Wireless Solar Keyboard K750", codename="K750", protocol=2.0, wpid="4002")
_D("Wireless Keyboard K270 (unifying)", codename="K270", protocol=2.0, wpid="4003")
_D("Wireless Keyboard K360", codename="K360", protocol=2.0, wpid="4004")
_D("Wireless Keyboard K230", codename="K230", protocol=2.0, wpid="400D")
_D("Wireless Touch Keyboard K400", codename="K400", protocol=2.0, wpid=("400E", "4024"))
_D("Wireless Keyboard MK270", codename="MK270", protocol=2.0, wpid="4023")
_D("Illuminated Living-Room Keyboard K830", codename="K830", protocol=2.0, wpid="4032")
_D("Wireless Touch Keyboard K400 Plus", codename="K400 Plus", protocol=2.0, wpid="404D")
_D("Wireless Multi-Device Keyboard K780", codename="K780", protocol=4.5, wpid="405B")
_D("Wireless Keyboard K375s", codename="K375s", protocol=2.0, wpid="4061")
_D("Craft Advanced Keyboard", codename="Craft", protocol=4.5, wpid="4066", btid=0xB350)
_D("Wireless Illuminated Keyboard K800 new", codename="K800 new", protocol=4.5, wpid="406E")
_D("Wireless Keyboard K470", codename="K470", protocol=4.5, wpid="4075")
_D("MX Keys Keyboard", codename="MX Keys", protocol=4.5, wpid="408A", btid=0xB35B)
_D(
    "G915 TKL LIGHTSPEED Wireless RGB Mechanical Gaming Keyboard",
    codename="G915 TKL",
    protocol=4.2,
    wpid="408E",
    usbid=0xC343,
)
_D("Illuminated Keyboard", codename="Illuminated", protocol=1.0, usbid=0xC318, interface=1)
_D("G213 Prodigy Gaming Keyboard", codename="G213", usbid=0xC336, interface=1)
_D("G512 RGB Mechanical Gaming Keyboard", codename="G512", usbid=0xC33C, interface=1)
_D("G815 Mechanical Keyboard", codename="G815", usbid=0xC33F, interface=1)
_D("diNovo Edge Keyboard", codename="diNovo", protocol=1.0, wpid="C714")
_D("K845 Mechanical Keyboard", codename="K845", usbid=0xC341, interface=3)

# Mice

_D("LX5 Cordless Mouse", codename="LX5", protocol=1.0, wpid="0036", registers=(Reg.BATTERY_STATUS,))
_D("LX7 Cordless Laser Mouse", codename="LX7", protocol=1.0, wpid="0039", registers=(Reg.BATTERY_STATUS,))
_D("Wireless Wave Mouse M550", codename="M550", protocol=1.0, wpid="003C", registers=(Reg.BATTERY_STATUS,))
_D("Wireless Mouse EX100", codename="EX100m", protocol=1.0, wpid="003F", registers=(Reg.BATTERY_STATUS,))
_D("Wireless Mouse M30", codename="M30", protocol=1.0, wpid="0085", registers=(Reg.BATTERY_STATUS,))
_D("MX610 Laser Cordless Mouse", codename="MX610", protocol=1.0, wpid="1001", registers=(Reg.BATTERY_STATUS,))
_D("G7 Cordless Laser Mouse", codename="G7", protocol=1.0, wpid="1002", registers=(Reg.BATTERY_STATUS,))
_D("V400 Laser Cordless Mouse", codename="V400", protocol=1.0, wpid="1003", registers=(Reg.BATTERY_STATUS,))
_D("MX610 Left-Handled Mouse", codename="MX610L", protocol=1.0, wpid="1004", registers=(Reg.BATTERY_STATUS,))
_D("V450 Laser Cordless Mouse", codename="V450", protocol=1.0, wpid="1005", registers=(Reg.BATTERY_STATUS,))
_D(
    "VX Revolution",
    codename="VX Revolution",
    kind=DEVICE_KIND.mouse,
    protocol=1.0,
    wpid=("1006", "100D", "0612"),
    registers=(Reg.BATTERY_CHARGE,),
)
_D(
    "MX Air",
    codename="MX Air",
    protocol=1.0,
    kind=DEVICE_KIND.mouse,
    wpid=("1007", "100E"),
    registers=Reg.BATTERY_CHARGE,
)
_D(
    "MX Revolution",
    codename="MX Revolution",
    protocol=1.0,
    kind=DEVICE_KIND.mouse,
    wpid=("1008", "100C"),
    registers=(Reg.BATTERY_CHARGE,),
)
_D(
    "MX620 Laser Cordless Mouse",
    codename="MX620",
    protocol=1.0,
    wpid=("100A", "1016"),
    registers=(Reg.BATTERY_CHARGE,),
)
_D(
    "VX Nano Cordless Laser Mouse",
    codename="VX Nano",
    protocol=1.0,
    wpid=("100B", "100F"),
    registers=(Reg.BATTERY_CHARGE,),
)
_D(
    "V450 Nano Cordless Laser Mouse",
    codename="V450 Nano",
    protocol=1.0,
    wpid="1011",
    registers=(Reg.BATTERY_CHARGE,),
)
_D(
    "V550 Nano Cordless Laser Mouse",
    codename="V550 Nano",
    protocol=1.0,
    wpid="1013",
    registers=(Reg.BATTERY_CHARGE,),
)
_D(
    "MX 1100 Cordless Laser Mouse",
    codename="MX 1100",
    protocol=1.0,
    kind=DEVICE_KIND.mouse,
    wpid="1014",
    registers=(Reg.BATTERY_CHARGE,),
)
_D("Anywhere Mouse MX", codename="Anywhere MX", protocol=1.0, wpid="1017", registers=(Reg.BATTERY_CHARGE,))
_D(
    "Performance Mouse MX",
    codename="Performance MX",
    protocol=1.0,
    wpid="101A",
    registers=(Reg.BATTERY_STATUS, Reg.THREE_LEDS),
)
_D(
    "Marathon Mouse M705 (M-R0009)",
    codename="M705 (M-R0009)",
    protocol=1.0,
    wpid="101B",
    registers=(Reg.BATTERY_CHARGE,),
)
_D(
    "Wireless Mouse M350",
    codename="M350",
    protocol=1.0,
    wpid="101C",
    registers=(Reg.BATTERY_CHARGE,),
)
_D(
    "Wireless Mouse M505",
    codename="M505/B605",
    protocol=1.0,
    wpid="101D",
    registers=(Reg.BATTERY_CHARGE,),
)
_D(
    "Wireless Mouse M305",
    codename="M305",
    protocol=1.0,
    wpid="101F",
    registers=(Reg.BATTERY_STATUS,),
)
_D(
    "Wireless Mouse M215",
    codename="M215",
    protocol=1.0,
    wpid="1020",
)
_D(
    "G700 Gaming Mouse",
    codename="G700",
    protocol=1.0,
    wpid="1023",
    usbid=0xC06B,
    interface=1,
    registers=(
        Reg.BATTERY_STATUS,
        Reg.THREE_LEDS,
    ),
)
_D("Wireless Mouse M310", codename="M310", protocol=1.0, wpid="1024", registers=(Reg.BATTERY_STATUS,))
_D("Wireless Mouse M510", codename="M510", protocol=1.0, wpid="1025", registers=(Reg.BATTERY_STATUS,))
_D("Fujitsu Sonic Mouse", codename="Sonic", protocol=1.0, wpid="1029")
_D(
    "G700s Gaming Mouse",
    codename="G700s",
    protocol=1.0,
    wpid="102A",
    usbid=0xC07C,
    interface=1,
    registers=(
        Reg.BATTERY_STATUS,
        Reg.THREE_LEDS,
    ),
)
_D("Couch Mouse M515", codename="M515", protocol=2.0, wpid="4007")
_D("Wireless Mouse M175", codename="M175", protocol=2.0, wpid="4008")
_D("Wireless Mouse M325", codename="M325", protocol=2.0, wpid="400A")
_D("Wireless Mouse M525", codename="M525", protocol=2.0, wpid="4013")
_D("Wireless Mouse M345", codename="M345", protocol=2.0, wpid="4017")
_D("Wireless Mouse M187", codename="M187", protocol=2.0, wpid="4019")
_D("Touch Mouse M600", codename="M600", protocol=2.0, wpid="401A")
_D("Wireless Mouse M150", codename="M150", protocol=2.0, wpid="4022")
_D("Wireless Mouse M185", codename="M185", protocol=2.0, wpid="4038")
_D("Wireless Mouse MX Master", codename="MX Master", protocol=4.5, wpid="4041", btid=0xB012)
_D("Anywhere Mouse MX 2", codename="Anywhere MX 2", protocol=4.5, wpid="404A")
_D("Wireless Mouse M510", codename="M510v2", protocol=2.0, wpid="4051")
_D("Wireless Mouse M185 new", codename="M185n", protocol=4.5, wpid="4054")
_D("Wireless Mouse M185/M235/M310", codename="M185/M235/M310", protocol=4.5, wpid="4055")
_D("Wireless Mouse MX Master 2S", codename="MX Master 2S", protocol=4.5, wpid="4069", btid=0xB019)
_D("Multi Device Silent Mouse M585/M590", codename="M585/M590", protocol=4.5, wpid="406B")
_D(
    "Marathon Mouse M705 (M-R0073)",
    codename="M705 (M-R0073)",
    protocol=4.5,
    wpid="406D",
)
_D("MX Vertical Wireless Mouse", codename="MX Vertical", protocol=4.5, wpid="407B", btid=0xB020, usbid=0xC08A)
_D("Wireless Mouse Pebble M350", codename="Pebble", protocol=2.0, wpid="4080")
_D("MX Master 3 Wireless Mouse", codename="MX Master 3", protocol=4.5, wpid="4082", btid=0xB023)
_D("PRO X Wireless", kind="mouse", codename="PRO X", wpid="4093", usbid=0xC094)

_D("G9 Laser Mouse", codename="G9", usbid=0xC048, interface=1, protocol=1.0)
_D("G9x Laser Mouse", codename="G9x", usbid=0xC066, interface=1, protocol=1.0)
_D("G502 Gaming Mouse", codename="G502", usbid=0xC07D, interface=1)
_D("G402 Gaming Mouse", codename="G402", usbid=0xC07E, interface=1)
_D("G900 Chaos Spectrum Gaming Mouse", codename="G900", usbid=0xC081)
_D("G403 Gaming Mouse", codename="G403", usbid=0xC082)
_D("G903 Lightspeed Gaming Mouse", codename="G903", usbid=0xC086)
_D("G703 Lightspeed Gaming Mouse", codename="G703", usbid=0xC087)
_D("GPro Gaming Mouse", codename="GPro", usbid=0xC088)
_D("G502 SE Hero Gaming Mouse", codename="G502 Hero", usbid=0xC08B, interface=1)
_D("G502 Lightspeed Gaming Mouse", codename="G502 Lightspeed", usbid=0xC08D)
_D("MX518 Gaming Mouse", codename="MX518", usbid=0xC08E, interface=1)
_D("G703 Hero Gaming Mouse", codename="G703 Hero", usbid=0xC090)
_D("G903 Hero Gaming Mouse", codename="G903 Hero", usbid=0xC091)
_D(None, kind=DEVICE_KIND.mouse, usbid=0xC092, interface=1)  # two mice share this ID
_D("M500S Mouse", codename="M500S", usbid=0xC093, interface=1)
# _D('G600 Gaming Mouse', codename='G600 Gaming', usbid=0xc24a, interface=1) # not an HID++ device
_D("G500s Gaming Mouse", codename="G500s Gaming", usbid=0xC24E, interface=1, protocol=1.0)
_D("G502 Proteus Spectrum Optical Mouse", codename="G502 Proteus Spectrum", usbid=0xC332, interface=1)
_D("Logitech PRO Gaming Keyboard", codename="PRO Gaming Keyboard", usbid=0xC339, interface=1)

_D("Logitech MX Revolution Mouse M-RCL 124", codename="M-RCL 124", btid=0xB007, interface=1)

# Trackballs

_D("Wireless Trackball M570", codename="M570")

# Touchpads

_D("Wireless Touchpad", codename="Wireless Touch", protocol=2.0, wpid="4011")
_D("Wireless Rechargeable Touchpad T650", codename="T650", protocol=2.0, wpid="4101")
_D(
    "G Powerplay", codename="Powerplay", protocol=2.0, kind=DEVICE_KIND.touchpad, wpid="405F"
)  # To override self-identification

# Headset

_D("G533 Gaming Headset", codename="G533 Headset", protocol=2.0, interface=3, kind=DEVICE_KIND.headset, usbid=0x0A66)
_D("G535 Gaming Headset", codename="G535 Headset", protocol=2.0, interface=3, kind=DEVICE_KIND.headset, usbid=0x0AC4)
_D("G935 Gaming Headset", codename="G935 Headset", protocol=2.0, interface=3, kind=DEVICE_KIND.headset, usbid=0x0A87)
_D("G733 Gaming Headset", codename="G733 Headset", protocol=2.0, interface=3, kind=DEVICE_KIND.headset, usbid=0x0AB5)
_D(
    "G733 Gaming Headset",
    codename="G733 Headset New",
    protocol=2.0,
    interface=3,
    kind=DEVICE_KIND.headset,
    usbid=0x0AFE,
)
_D(
    "PRO X Wireless Gaming Headset",
    codename="PRO Headset",
    protocol=2.0,
    interface=3,
    kind=DEVICE_KIND.headset,
    usbid=0x0ABA,
)
