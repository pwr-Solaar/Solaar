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
        raise OSError(errno.ACCESS, "Fake access error")
    return int(path, 16)  # can raise exception


@dataclass
class Response:
    response: Optional[str]
    id: int
    params: str = ""
    handle: int = 0x11
    devnumber: int = 0xFF
    no_reply: bool = False


def replace_number(responses, number):  # change the devnumber for a list of responses
    return [Response(r.response, r.id, r.params, r.handle, number, r.no_reply) for r in responses]


def ping(responses, handle, devnumber, long_message=False):
    print("PING ", hex(handle), hex(devnumber) if devnumber else devnumber)
    for r in responses:
        if handle == r.handle and devnumber == r.devnumber and r.id == 0x0010:
            print("RESPONSE", hex(r.handle), hex(r.devnumber), r.response)
            return r.response


def request(responses, handle, devnumber, id, *params, no_reply=False, return_error=False, long_message=False, protocol=1.0):
    params = b"".join(pack("B", p) if isinstance(p, int) else p for p in params)
    print("REQUEST ", hex(handle), hex(devnumber), hex(id), params.hex())
    for r in responses:
        if handle == r.handle and devnumber == r.devnumber and r.id == id and bytes.fromhex(r.params) == params:
            print("RESPONSE", hex(r.handle), hex(r.devnumber), hex(r.id), r.params, r.response)
            return bytes.fromhex(r.response) if r.response is not None else None


r_empty = [  # a HID++ device with no responses except for ping
    Response(1.0, 0x0010),  # ping
]

r_keyboard_1 = [  # a HID++ 1.0 keyboard
    Response(1.0, 0x0010),  # ping
    Response("001234", 0x81F1, "01"),  # firmware
    Response("003412", 0x81F1, "02"),  # firmware
    Response("002345", 0x81F1, "03"),  # firmware
    Response("003456", 0x81F1, "04"),  # firmware
]

r_keyboard_2 = [  # a HID++ 2.0 keyboard
    Response(4.2, 0x0010),  # ping
    Response("010001", 0x0000, "0001"),  # feature set at 0x01
    Response("020003", 0x0000, "1000"),  # battery status at 0x02
    Response("030001", 0x0000, "0003"),  # device information at 0x03
    Response("040003", 0x0000, "0100"),  # unknown 0100 at 0x04
    Response("050003", 0x0000, "1B04"),  # reprogrammable keys V4 at 0x05
    Response("08", 0x0100),  # 8 features
    Response("00010001", 0x0110, "01"),  # feature set at 0x01
    Response("10000001", 0x0110, "02"),  # battery status at 0x02
    Response("00030001", 0x0110, "03"),  # device information at 0x03
    Response("01000003", 0x0110, "04"),  # unknown 0100 at 0x04
    Response("1B040003", 0x0110, "05"),  # reprogrammable keys V4 at 0x05
    Response("0212345678000D1234567890ABAA01", 0x0300),  # device information
    Response("00110012AB010203CD00", 0x0510, "00"),  # reprogrammable keys V4
    Response("01110022AB010203CD00", 0x0510, "01"),  # reprogrammable keys V4
    Response("00010111AB010203CD00", 0x0510, "02"),  # reprogrammable keys V4
    Response("03110032AB010204CD00", 0x0510, "03"),  # reprogrammable keys V4
    Response("00030333AB010203CD00", 0x0510, "04"),  # reprogrammable keys V4
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
    settings = []
    sliding = profiles = _backlight = _keys = _remap_keys = _led_effects = _gestures = None
    _gestures_lock = threading.Lock()

    read_register = device.Device.read_register
    write_register = device.Device.write_register
    backlight = device.Device.backlight
    keys = device.Device.keys
    remap_keys = device.Device.remap_keys
    led_effects = device.Device.led_effects
    gestures = device.Device.gestures
    __hash__ = device.Device.__hash__

    def __post_init__(self):
        self.persister = configuration._DeviceEntry()
        if self.feature is not None:
            self.features = hidpp20.FeaturesArray(self)
            self.responses = [Response("010001", 0x0000, "0001"), Response("20", 0x0100)] + self.responses
            self.responses.append(Response(f"{self.offset:0>2X}00{self.version:0>2X}", 0x0000, f"{self.feature:0>4X}"))
        if self.setting_callback is None:
            self.setting_callback = lambda x, y, z: None
        self.add_notification_handler = lambda x, y: None

    def request(self, id, *params, no_reply=False):
        if params is None:
            params = []
        params = b"".join(pack("B", p) if isinstance(p, int) else p for p in params)
        print("REQUEST ", self.name, hex(id), params.hex().upper())
        for r in self.responses:
            if id == r.id and params == bytes.fromhex(r.params):
                print("RESPONSE", self.name, hex(r.id), r.params, r.response)
                return bytes.fromhex(r.response) if isinstance(r.response, str) else r.response
        print("RESPONSE", self.name, None)

    def feature_request(self, feature, function=0x00, *params, no_reply=False):
        if self.protocol >= 2.0:
            return hidpp20.feature_request(self, feature, function, *params, no_reply=no_reply)
