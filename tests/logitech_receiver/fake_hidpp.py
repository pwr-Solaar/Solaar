## Copyright (C) 2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
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

"""HID++ data and functions common to several logitech_receiver test files"""

from __future__ import annotations

import errno
import threading

from dataclasses import dataclass
from dataclasses import field
from struct import pack
from typing import Any
from typing import Optional

from logitech_receiver import device
from logitech_receiver import hidpp20
from solaar import configuration


def open_path(path: Optional[str]) -> int:
    if path is None:
        raise OSError(errno.EACCES, "Fake access error")
    return int(path, 16)  # can raise exception


def ping(responses, handle, devnumber, long_message=False):
    for r in responses:
        if handle == r.handle and devnumber == r.devnumber and r.id == 0x0010:
            return r.response


def request(
    responses,
    handle,
    devnumber,
    id,
    *params,
    no_reply=False,
    return_error=False,
    long_message=False,
    protocol=1.0,
):
    params = b"".join(pack("B", p) if isinstance(p, int) else p for p in params)
    print("REQUEST ", hex(handle), hex(devnumber), hex(id), params.hex())
    for r in responses:
        if handle == r.handle and devnumber == r.devnumber and r.id == id and bytes.fromhex(r.params) == params:
            print("RESPONSE", hex(r.handle), hex(r.devnumber), hex(r.id), r.params, r.response)
            return bytes.fromhex(r.response) if r.response is not None else None


@dataclass
class Response:
    response: str | float
    id: int
    params: str = ""
    handle: int = 0x11
    devnumber: int = 0xFF
    no_reply: bool = False


def replace_number(responses, number):  # change the devnumber for a list of responses
    return [Response(r.response, r.id, r.params, r.handle, number, r.no_reply) for r in responses]


def adjust_responses_index(index, responses):  # change index-4 responses to index
    return [Response(r.response, r.id - 0x400 + (index << 8), r.params, r.handle, r.devnumber, r.no_reply) for r in responses]


r_empty = [  # a HID++ device with no responses except for ping
    Response(1.0, 0x0010),  # ping
]

r_keyboard_1 = [  # a HID++ 1.0 keyboard
    Response(1.0, 0x0010),  # ping
    Response("001234", 0x81F1, "01"),  # firmware
    Response("003412", 0x81F1, "02"),  # firmware
    Response("002345", 0x81F1, "03"),  # firmware
    Response("003456", 0x81F1, "04"),  # firmware
    Response("050050", 0x8107),  # battery status
]

r_keyboard_2 = [  # a HID++ 2.0 keyboard
    Response(4.2, 0x0010),  # ping
    Response("010001", 0x0000, "0001"),  # feature set at 0x01
    Response("020003", 0x0000, "0020"),  # CONFIG_CHANGE at 0x02
    Response("030001", 0x0000, "0003"),  # device information at 0x03
    Response("040003", 0x0000, "0100"),  # unknown 0100 at 0x04
    Response("050003", 0x0000, "1B04"),  # reprogrammable keys V4 at 0x05
    Response("060003", 0x0000, "0007"),  # device friendly name at 0x06
    Response("070003", 0x0000, "0005"),  # device name at 0x07
    Response("080003", 0x0000, "1000"),  # battery status at 0x08
    Response("08", 0x0100),  # 8 features
    Response("00010001", 0x0110, "01"),  # feature set at 0x01
    Response("00200003", 0x0110, "02"),  # CONFIG_CHANGE at 0x02
    Response("00030001", 0x0110, "03"),  # device information at 0x03
    Response("01000003", 0x0110, "04"),  # unknown 0100 at 0x04
    Response("1B040003", 0x0110, "05"),  # reprogrammable keys V4 at 0x05
    Response("00070003", 0x0000, "06"),  # device friendly name at 0x06
    Response("00050003", 0x0000, "07"),  # device name at 0x07
    Response("10000001", 0x0110, "08"),  # battery status at 0x02
    Response("0212345678000D1234567890ABAA01", 0x0300),  # device information
    Response("04", 0x0500),  # reprogrammable keys V4
    Response("00110012AB010203CD00", 0x0510, "00"),  # reprogrammable keys V4
    Response("01110022AB010203CD00", 0x0510, "01"),  # reprogrammable keys V4
    Response("00010111AB010203CD00", 0x0510, "02"),  # reprogrammable keys V4
    Response("03110032AB010204CD00", 0x0510, "03"),  # reprogrammable keys V4
    Response("00030333AB010203CD00", 0x0510, "04"),  # reprogrammable keys V4
    Response("12", 0x0600),  # friendly namme
    Response("004142434445464748494A4B4C4D4E", 0x0610, "00"),
    Response("0E4F50515253000000000000000000", 0x0610, "0E"),
    Response("12", 0x0700),  # name and kind
    Response("4142434445464748494A4B4C4D4E4F", 0x0710, "00"),
    Response("505152530000000000000000000000", 0x0710, "0F"),
    Response("00", 0x0720),
    Response("12345678", 0x0800),  # battery status
]

r_mouse_1 = [  # a HID++ 1.0 mouse
    Response(1.0, 0x0010),  # ping
]

r_mouse_2 = [  # a HID++ 2.0 mouse with few responses except for ping
    Response(4.2, 0x0010),  # ping
]

r_mouse_3 = [  # a HID++ 2.0 mouse
    Response(4.5, 0x0010),  # ping
    Response("010001", 0x0000, "0001"),  # feature set at 0x01
    Response("020002", 0x0000, "8060"),  # report rate at 0x02
    Response("040001", 0x0000, "0003"),  # device information at 0x04
    Response("050002", 0x0000, "0005"),  # device type and name at 0x05
    Response("08", 0x0100),  # 8 features
    Response("00010001", 0x0110, "01"),  # feature set at 0x01
    Response("80600002", 0x0110, "02"),  # report rate at 0x02
    Response("00030001", 0x0110, "04"),  # device information at 0x04
    Response("00050002", 0x0110, "05"),  # device type and name at 0x05
    Response("09", 0x0210),  # report rate - current rate
    Response("03123456790008123456780000AA01", 0x0400),  # device information
    Response("0141424302030100", 0x0410, "00"),  # firmware 0
    Response("0241", 0x0410, "01"),  # firmware 1
    Response("05", 0x0410, "02"),  # firmware 2
    Response("12", 0x0500),  # name count - 18 characters
    Response("414241424142414241424142414241", 0x0510, "00"),  # name - first 15 characters
    Response("444544000000000000000000000000", 0x0510, "0F"),  # name - last 3 characters
]


responses_key = [  # responses for Reprogrammable Keys V4 at 0x05
    Response("08", 0x0500),  # Reprogrammable Keys V4 count
    Response("00500038010001010400000000000000", 0x0510, "00"),  # left button
    Response("00510039010001010400000000000000", 0x0510, "01"),  # right button
    Response("0052003A310003070500000000000000", 0x0510, "02"),  # middle button
    Response("0053003C710002030100000000000000", 0x0510, "03"),  # back button
    Response("0056003E710002030100000000000000", 0x0510, "04"),  # forward button
    Response("00C300A9310003070300000000000000", 0x0510, "05"),  # smart shift?
    Response("00C4009D310003070500000000000000", 0x0510, "06"),  # ?
    Response("00D700B4A00004000300000000000000", 0x0510, "07"),  # ?
    Response("00500000000000000000000000000000", 0x0520, "0050"),  # left button
    Response("00510000000000000000000000000000", 0x0520, "0051"),  # ...
    Response("00520100500000000000000000000000", 0x0520, "0052"),
    Response("00530500000000000000000000000000", 0x0520, "0053"),
    Response("00561100000000000000000000000000", 0x0520, "0056"),
    Response("00C30000000000000000000000000000", 0x0520, "00C3"),
    Response("00C40000500000000000000000000000", 0x0520, "00C4"),
    Response("00D70000510000000000000000000000", 0x0520, "00D7"),
    Response("0041", 0x0400),  # flags
    Response("0401", 0x0410),  # count
    Response("0050", 0x0420, "00FF"),  # left button
    Response("0051", 0x0420, "01FF"),  # right button
    Response("0052", 0x0420, "02FF"),  # middle button
    Response("0053", 0x0420, "03FF"),  # back button
    Response("0050000100500000", 0x0430, "0050FF"),  # left button current
    Response("0051000100500001", 0x0430, "0051FF"),  # right button current
    Response("0052000100500001", 0x0430, "0052FF"),  # middle button current
    Response("0053000100500001", 0x0430, "0053FF"),  # back button current
    Response("0050FF01005000", 0x0440, "0050FF01005000"),  # left button write
    Response("0051FF01005000", 0x0440, "0051FF01005000"),  # right button write
    Response("0051FF01005100", 0x0440, "0051FF01005100"),  # right button set write
]

responses_remap = [  # responses for Persistent Remappable Actions at 0x04 and reprogrammable keys at 0x05
    Response("0041", 0x0400),
    Response("03", 0x0410),
    Response("0301", 0x0410, "00"),
    Response("0050", 0x0420, "00FF"),
    Response("0050000200010001", 0x0430, "0050FF"),  # Left Button
    Response("0051", 0x0420, "01FF"),
    Response("0051000200010000", 0x0430, "0051FF"),  # Left Button
    Response("0052", 0x0420, "02FF"),
    Response("0052000100510000", 0x0430, "0052FF"),  # key DOWN
    Response("050002", 0x0000, "1B04"),  # REPROGRAMMABLE_KEYS_V4
] + responses_key

responses_gestures = [  # the commented-out messages are not used by either the setting or other testing
    Response("4203410141020400320480148C21A301", 0x0400, "0000"),  # items
    Response("A302A11EA30A4105822C852DAD2AAD2B", 0x0400, "0008"),
    Response("8F408F418F434204AF54912282558264", 0x0400, "0010"),
    Response("01000000000000000000000000000000", 0x0400, "0018"),
    Response("01000000000000000000000000000000", 0x0410, "000101"),  # enable
    #    Response("02000000000000000000000000000000", 0x0410, "000102"),
    #    Response("04000000000000000000000000000000", 0x0410, "000104"),
    #    Response("08000000000000000000000000000000", 0x0410, "000108"),
    Response("00000000000000000000000000000000", 0x0410, "000110"),
    #    Response("20000000000000000000000000000000", 0x0410, "000120"),
    #    Response("40000000000000000000000000000000", 0x0410, "000140"),
    #    Response("00000000000000000000000000000000", 0x0410, "000180"),
    #    Response("00000000000000000000000000000000", 0x0410, "010101"),
    #    Response("00000000000000000000000000000000", 0x0410, "010102"),
    #    Response("04000000000000000000000000000000", 0x0410, "010104"),
    #    Response("00000000000000000000000000000000", 0x0410, "010108"),
    Response("6F000000000000000000000000000000", 0x0410, "0001FF"),
    Response("04000000000000000000000000000000", 0x0410, "01010F"),
    Response("00000000000000000000000000000000", 0x0430, "000101"),  # divert
    #    Response("00000000000000000000000000000000", 0x0430, "000102"),
    #    Response("00000000000000000000000000000000", 0x0430, "000104"),
    #    Response("00000000000000000000000000000000", 0x0430, "000108"),
    Response("00000000000000000000000000000000", 0x0430, "000110"),
    #    Response("00000000000000000000000000000000", 0x0430, "000120"),
    #    Response("00000000000000000000000000000000", 0x0430, "000140"),
    #    Response("00000000000000000000000000000000", 0x0430, "000180"),
    #    Response("00000000000000000000000000000000", 0x0430, "010101"),
    #    Response("00000000000000000000000000000000", 0x0430, "010102"),
    Response("00000000000000000000000000000000", 0x0430, "0001FF"),
    Response("00000000000000000000000000000000", 0x0430, "010103"),
    Response("08000000000000000000000000000000", 0x0450, "01FF"),
    Response("08000000000000000000000000000000", 0x0450, "02FF"),
    Response("08000000000000000000000000000000", 0x0450, "03FF"),
    Response("00040000000000000000000000000000", 0x0450, "04FF"),
    Response("5C020000000000000000000000000000", 0x0450, "05FF"),
    Response("01000000000000000000000000000000", 0x0460, "00FF"),
    Response("01000000000000000000000000000000", 0x0470, "00FF"),
    Response("01", 0x0420, "00010101"),  # set index 1
    Response("00", 0x0420, "00010100"),  # unset index 1
    Response("01", 0x0420, "00011010"),  # set index 4
    Response("00", 0x0420, "00011000"),  # unset index 4
    Response("01", 0x0440, "00010101"),  # divert index 1
    Response("00", 0x0440, "00010100"),  # undivert index 1
    Response("000080FF", 0x0480, "000080FF"),  # write param 0
    Response("000180FF", 0x0480, "000180FF"),  # write param 0
]

zone_responses_1 = [  # responses for COLOR LED EFFECTS
    Response("00000102", 0x0710, "00FF00"),
    Response("0000000300040005", 0x0720, "000000"),
    Response("0001000B00080009", 0x0720, "000100"),
]
zone_responses_2 = [  # responses for RGB EFFECTS
    Response("0000000102", 0x0700, "00FF00"),
    Response("0000000300040005", 0x0700, "000000"),
    Response("0001000200080009", 0x0700, "000100"),
]
effects_responses_1 = [Response("0100000001", 0x0700)] + zone_responses_1
effects_responses_2 = [Response("FFFF0100000001", 0x0700, "FFFF00")] + zone_responses_2

responses_profiles = [  # OnboardProfile in RAM
    Response("0104010101020100FE0200", 0x0900),
    Response("000101FF", 0x0950, "00000000"),
    Response("FFFFFFFF", 0x0950, "00000004"),
    Response("01010290018003000700140028FFFFFF", 0x0950, "00010000"),
    Response("FFFF0000000000000000000000000000", 0x0950, "00010010"),
    Response("8000FFFF900aFF00800204548000FFFF", 0x0950, "00010020"),
    Response("900aFF00800204548000FFFF900aFF00", 0x0950, "00010030"),
    Response("800204548000FFFF900aFF0080020454", 0x0950, "00010040"),
    Response("8000FFFF900aFF00800204548000FFFF", 0x0950, "00010050"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0950, "00010060"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0950, "00010070"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0950, "00010080"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0950, "00010090"),
    Response("54004500370000000000000000000000", 0x0950, "000100A0"),
    Response("00000000000000000000000000000000", 0x0950, "000100B0"),
    Response("00000000000000000000000000000000", 0x0950, "000100C0"),
    Response("0A01020300500407000000FFFFFFFFFF", 0x0950, "000100D0"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0950, "000100E0"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFF7C81AB", 0x0950, "000100EE"),
]
responses_profiles_rom = [  # OnboardProfile in ROM
    Response("0104010101020100FE0200", 0x0900),
    Response("00000000", 0x0950, "00000000"),
    Response("010101FF", 0x0950, "01000000"),
    Response("FFFFFFFF", 0x0950, "01000004"),
    Response("01010290018003000700140028FFFFFF", 0x0950, "01010000"),
    Response("FFFF0000000000000000000000000000", 0x0950, "01010010"),
    Response("8000FFFF900aFF00800204548000FFFF", 0x0950, "01010020"),
    Response("900aFF00800204548000FFFF900aFF00", 0x0950, "01010030"),
    Response("800204548000FFFF900aFF0080020454", 0x0950, "01010040"),
    Response("8000FFFF900aFF00800204548000FFFF", 0x0950, "01010050"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0950, "01010060"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0950, "01010070"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0950, "01010080"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0950, "01010090"),
    Response("54004500370000000000000000000000", 0x0950, "010100A0"),
    Response("00000000000000000000000000000000", 0x0950, "010100B0"),
    Response("00000000000000000000000000000000", 0x0950, "010100C0"),
    Response("0A01020300500407000000FFFFFFFFFF", 0x0950, "010100D0"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0950, "010100E0"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFF7C81AB", 0x0950, "010100EE"),
]
responses_profiles_rom_2 = [  # OnboardProfile in ROM
    Response("0104010101020100FE0200", 0x0900),
    Response("FFFFFFFF", 0x0950, "00000000"),
    Response("010101FF", 0x0950, "01000000"),
    Response("FFFFFFFF", 0x0950, "01000004"),
    Response("01010290018003000700140028FFFFFF", 0x0950, "01010000"),
    Response("FFFF0000000000000000000000000000", 0x0950, "01010010"),
    Response("8000FFFF900aFF00800204548000FFFF", 0x0950, "01010020"),
    Response("900aFF00800204548000FFFF900aFF00", 0x0950, "01010030"),
    Response("800204548000FFFF900aFF0080020454", 0x0950, "01010040"),
    Response("8000FFFF900aFF00800204548000FFFF", 0x0950, "01010050"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0950, "01010060"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0950, "01010070"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0950, "01010080"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0950, "01010090"),
    Response("54004500370000000000000000000000", 0x0950, "010100A0"),
    Response("00000000000000000000000000000000", 0x0950, "010100B0"),
    Response("00000000000000000000000000000000", 0x0950, "010100C0"),
    Response("0A01020300500407000000FFFFFFFFFF", 0x0950, "010100D0"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0950, "010100E0"),
    Response("FFFFFFFFFFFFFFFFFFFFFFFFFF7C81AB", 0x0950, "010100EE"),
]

complex_responses_1 = [  # COLOR_LED_EFFECTS
    Response(4.2, 0x0010),  # ping
    Response("010001", 0x0000, "0001"),  # FEATURE SET at x01
    Response("020001", 0x0000, "0020"),  # CONFIG_CHANGE at x02
    Response("0A", 0x0100),  # 10 features
    Response("070001", 0x0000, "8070"),  # COLOR_LED_EFFECTS at 0x07
    *effects_responses_1,
]

complex_responses_2 = [  # RGB_EFFECTS + reprogrammable keys + persistent actions
    Response(4.2, 0x0010),  # ping
    Response("010001", 0x0000, "0001"),  # FEATURE SET at x01
    Response("020001", 0x0000, "0020"),  # CONFIG_CHANGE at x02
    Response("0A", 0x0100),  # 10 features
    Response("070001", 0x0000, "8071"),  # RGB_EFFECTS at 0x07
    *effects_responses_2,
    Response("040001", 0x0000, "1C00"),  # Persistent Remappable Actions at 0x04
    *responses_remap,
    Response("080001", 0x0000, "6501"),  # Gestures at 0x08
    *adjust_responses_index(8, responses_gestures),
    Response("060003", 0x0000, "1982"),  # Backlight 2 at 0x06
    Response("010118000001020003000400", 0x0600),
    Response("090003", 0x0000, "8100"),  # Onboard Profiles at 0x09
    *responses_profiles,
]

responses_speedchange = [
    Response("0100", 0x0400),
    Response("010001", 0x0000, "0001"),  # FEATURE SET at x01
    Response("0A", 0x0100),  # 10 features
    Response("0120", 0x0410, "0120"),
    Response("050001", 0x0000, "1B04"),  # REPROG_CONTROLS_V4
    Response("01", 0x0500),
    Response("00ED009D310003070500000000000000", 0x0510, "00"),  # DPI Change
    Response("00ED0000000000000000000000000000", 0x0520, "00ED"),  # DPI Change current
    Response("060000", 0x0000, "2205"),  # POINTER_SPEED
]


# A fake device that uses provided data (responses) to respond to HID++ commands.
# Some methods from the real device are used to set up data structures needed for settings
@dataclass
class Device:
    name: str = "TESTD"
    online: bool = True
    protocol: float = 2.0
    responses: Any = field(default_factory=list)
    codename: str = "TESTC"
    feature: Optional[int] = None
    offset: Optional[int] = 4
    version: Optional[int] = 0
    wpid: Optional[str] = "0000"
    setting_callback: Any = None
    sliding = profiles = _backlight = _keys = _remap_keys = _led_effects = _gestures = None
    _gestures_lock = threading.Lock()
    number = "d1"

    read_register = device.Device.read_register
    write_register = device.Device.write_register
    backlight = device.Device.backlight
    keys = device.Device.keys
    remap_keys = device.Device.remap_keys
    led_effects = device.Device.led_effects
    gestures = device.Device.gestures
    __hash__ = device.Device.__hash__
    feature_request = device.Device.feature_request

    def __post_init__(self):
        self._name = self.name
        self._protocol = self.protocol
        self.persister = configuration._DeviceEntry()
        self.features = hidpp20.FeaturesArray(self)
        self.settings = []
        self.receiver = []
        if self.feature is not None:
            self.features = hidpp20.FeaturesArray(self)
            self.responses = [
                Response("010001", 0x0000, "0001"),
                Response("20", 0x0100),
            ] + self.responses
            self.responses.append(
                Response(
                    f"{int(self.offset):0>2X}00{int(self.version):0>2X}",
                    0x0000,
                    f"{int(self.feature):0>4X}",
                )
            )
        if self.setting_callback is None:
            self.setting_callback = lambda x, y, z: None
        self.add_notification_handler = lambda x, y: None

    def request(self, id, *params, no_reply=False, long_message=False, protocol=2.0):
        params = b"".join(pack("B", p) if isinstance(p, int) else p for p in params)
        print("REQUEST ", self._name, hex(id), params.hex().upper())
        for r in self.responses:
            if id == r.id and params == bytes.fromhex(r.params):
                print("RESPONSE", self._name, hex(r.id), r.params, r.response)
                return bytes.fromhex(r.response) if isinstance(r.response, str) else r.response
        print("RESPONSE", self._name, None)

    def ping(self, handle=None, devnumber=None, long_message=False):
        print("PING", self._protocol)
        return self._protocol

    def handle_notification(self, handle):
        pass

    def changed(self, *args, **kwargs):
        pass

    def set_battery_info(self, *args, **kwargs):
        pass

    def status_string(self):
        pass


def match_requests(number, responses, call_args_list):
    for i in range(0 - number, 0):
        param = b"".join(pack("B", p) if isinstance(p, int) else p for p in call_args_list[i][0][1:]).hex().upper()
        print("MATCH", i, hex(call_args_list[i][0][0]), param, hex(responses[i].id), responses[i].params)
        assert call_args_list[i][0][0] == responses[i].id
        assert param == responses[i].params
