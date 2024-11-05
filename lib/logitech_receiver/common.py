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

import binascii
import dataclasses
import typing

from enum import Flag
from enum import IntEnum
from typing import Generator
from typing import Iterable
from typing import Optional
from typing import Union

import yaml

from solaar.i18n import _

if typing.TYPE_CHECKING:
    from logitech_receiver.hidpp20_constants import FirmwareKind

LOGITECH_VENDOR_ID = 0x046D


def crc16(data: bytes):
    """
    CRC-16 (CCITT) implemented with a precomputed lookup table
    """
    table = [
        0x0000,
        0x1021,
        0x2042,
        0x3063,
        0x4084,
        0x50A5,
        0x60C6,
        0x70E7,
        0x8108,
        0x9129,
        0xA14A,
        0xB16B,
        0xC18C,
        0xD1AD,
        0xE1CE,
        0xF1EF,
        0x1231,
        0x0210,
        0x3273,
        0x2252,
        0x52B5,
        0x4294,
        0x72F7,
        0x62D6,
        0x9339,
        0x8318,
        0xB37B,
        0xA35A,
        0xD3BD,
        0xC39C,
        0xF3FF,
        0xE3DE,
        0x2462,
        0x3443,
        0x0420,
        0x1401,
        0x64E6,
        0x74C7,
        0x44A4,
        0x5485,
        0xA56A,
        0xB54B,
        0x8528,
        0x9509,
        0xE5EE,
        0xF5CF,
        0xC5AC,
        0xD58D,
        0x3653,
        0x2672,
        0x1611,
        0x0630,
        0x76D7,
        0x66F6,
        0x5695,
        0x46B4,
        0xB75B,
        0xA77A,
        0x9719,
        0x8738,
        0xF7DF,
        0xE7FE,
        0xD79D,
        0xC7BC,
        0x48C4,
        0x58E5,
        0x6886,
        0x78A7,
        0x0840,
        0x1861,
        0x2802,
        0x3823,
        0xC9CC,
        0xD9ED,
        0xE98E,
        0xF9AF,
        0x8948,
        0x9969,
        0xA90A,
        0xB92B,
        0x5AF5,
        0x4AD4,
        0x7AB7,
        0x6A96,
        0x1A71,
        0x0A50,
        0x3A33,
        0x2A12,
        0xDBFD,
        0xCBDC,
        0xFBBF,
        0xEB9E,
        0x9B79,
        0x8B58,
        0xBB3B,
        0xAB1A,
        0x6CA6,
        0x7C87,
        0x4CE4,
        0x5CC5,
        0x2C22,
        0x3C03,
        0x0C60,
        0x1C41,
        0xEDAE,
        0xFD8F,
        0xCDEC,
        0xDDCD,
        0xAD2A,
        0xBD0B,
        0x8D68,
        0x9D49,
        0x7E97,
        0x6EB6,
        0x5ED5,
        0x4EF4,
        0x3E13,
        0x2E32,
        0x1E51,
        0x0E70,
        0xFF9F,
        0xEFBE,
        0xDFDD,
        0xCFFC,
        0xBF1B,
        0xAF3A,
        0x9F59,
        0x8F78,
        0x9188,
        0x81A9,
        0xB1CA,
        0xA1EB,
        0xD10C,
        0xC12D,
        0xF14E,
        0xE16F,
        0x1080,
        0x00A1,
        0x30C2,
        0x20E3,
        0x5004,
        0x4025,
        0x7046,
        0x6067,
        0x83B9,
        0x9398,
        0xA3FB,
        0xB3DA,
        0xC33D,
        0xD31C,
        0xE37F,
        0xF35E,
        0x02B1,
        0x1290,
        0x22F3,
        0x32D2,
        0x4235,
        0x5214,
        0x6277,
        0x7256,
        0xB5EA,
        0xA5CB,
        0x95A8,
        0x8589,
        0xF56E,
        0xE54F,
        0xD52C,
        0xC50D,
        0x34E2,
        0x24C3,
        0x14A0,
        0x0481,
        0x7466,
        0x6447,
        0x5424,
        0x4405,
        0xA7DB,
        0xB7FA,
        0x8799,
        0x97B8,
        0xE75F,
        0xF77E,
        0xC71D,
        0xD73C,
        0x26D3,
        0x36F2,
        0x0691,
        0x16B0,
        0x6657,
        0x7676,
        0x4615,
        0x5634,
        0xD94C,
        0xC96D,
        0xF90E,
        0xE92F,
        0x99C8,
        0x89E9,
        0xB98A,
        0xA9AB,
        0x5844,
        0x4865,
        0x7806,
        0x6827,
        0x18C0,
        0x08E1,
        0x3882,
        0x28A3,
        0xCB7D,
        0xDB5C,
        0xEB3F,
        0xFB1E,
        0x8BF9,
        0x9BD8,
        0xABBB,
        0xBB9A,
        0x4A75,
        0x5A54,
        0x6A37,
        0x7A16,
        0x0AF1,
        0x1AD0,
        0x2AB3,
        0x3A92,
        0xFD2E,
        0xED0F,
        0xDD6C,
        0xCD4D,
        0xBDAA,
        0xAD8B,
        0x9DE8,
        0x8DC9,
        0x7C26,
        0x6C07,
        0x5C64,
        0x4C45,
        0x3CA2,
        0x2C83,
        0x1CE0,
        0x0CC1,
        0xEF1F,
        0xFF3E,
        0xCF5D,
        0xDF7C,
        0xAF9B,
        0xBFBA,
        0x8FD9,
        0x9FF8,
        0x6E17,
        0x7E36,
        0x4E55,
        0x5E74,
        0x2E93,
        0x3EB2,
        0x0ED1,
        0x1EF0,
    ]

    crc = 0xFFFF
    for byte in data:
        crc = (crc << 8) ^ table[(crc >> 8) ^ byte]
        crc &= 0xFFFF  # important, crc must stay 16bits all the way through
    return crc


class NamedInt(int):
    """A regular Python integer with an attached name.

    Caution: comparison with strings will also match this NamedInt's name
    (case-insensitive)."""

    def __new__(cls, value, name):
        assert isinstance(name, str)
        obj = int.__new__(cls, value)
        obj.name = str(name)
        return obj

    def bytes(self, count=2):
        return int2bytes(self, count)

    def __eq__(self, other):
        if other is None:
            return False
        if isinstance(other, NamedInt):
            return int(self) == int(other) and self.name == other.name
        if isinstance(other, int):
            return int(self) == int(other)
        if isinstance(other, str):
            return self.name.lower() == other.lower()
        # this should catch comparisons with bytes in Py3
        if other is not None:
            raise TypeError("Unsupported type " + str(type(other)))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return int(self)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"NamedInt({int(self)}, {self.name!r})"

    @classmethod
    def from_yaml(cls, loader, node):
        args = loader.construct_mapping(node)
        return cls(value=args["value"], name=args["name"])

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_mapping("!NamedInt", {"value": int(data), "name": data.name}, flow_style=True)


yaml.SafeLoader.add_constructor("!NamedInt", NamedInt.from_yaml)
yaml.add_representer(NamedInt, NamedInt.to_yaml)


class NamedInts:
    """An ordered set of NamedInt values.

    Indexing can be made by int or string, and will return the corresponding
    NamedInt if it exists in this set, or `None`.

    Extracting slices will return all present NamedInts in the given interval
    (extended slices are not supported).

    Assigning a string to an indexed int will create a new NamedInt in this set;
    if the value already exists in the set (int or string), ValueError will be
    raised.
    """

    __slots__ = ("__dict__", "_values", "_indexed", "_fallback", "_is_sorted")

    def __init__(self, dict_=None, **kwargs):
        def _readable_name(n):
            return n.replace("__", "/").replace("_", " ")

        # print (repr(kwargs))
        elements = dict_ if dict_ else kwargs
        values = {k: NamedInt(v, _readable_name(k)) for (k, v) in elements.items()}
        self.__dict__ = values
        self._is_sorted = False
        self._values = list(values.values())
        self._sort_values()
        self._indexed = {int(v): v for v in self._values}
        # assert len(values) == len(self._indexed)
        # "(%d) %r\n=> (%d) %r" % (len(values), values, len(self._indexed), self._indexed)
        self._fallback = None

    @classmethod
    def list(cls, items, name_generator=lambda x: str(x)):  # noqa: B008
        values = {name_generator(x): x for x in items}
        return NamedInts(**values)

    @classmethod
    def range(cls, from_value, to_value, name_generator=lambda x: str(x), step=1):  # noqa: B008
        values = {name_generator(x): x for x in range(from_value, to_value + 1, step)}
        return NamedInts(**values)

    def flag_names(self, value):
        unknown_bits = value
        for k in self._indexed:
            assert bin(k).count("1") == 1
            if k & value == k:
                unknown_bits &= ~k
                yield str(self._indexed[k])

        if unknown_bits:
            yield f"unknown:{unknown_bits:06X}"

    def _sort_values(self):
        self._values = sorted(self._values)
        self._is_sorted = True

    def __getitem__(self, index):
        if isinstance(index, int):
            if index in self._indexed:
                return self._indexed[int(index)]
            if self._fallback:
                value = NamedInt(index, self._fallback(index))
                self._indexed[index] = value
                self._values.append(value)
                self._is_sorted = False
                self._sort_values()
                return value

        elif isinstance(index, str):
            if index in self.__dict__:
                return self.__dict__[index]
            return next((x for x in self._values if str(x) == index), None)

        elif isinstance(index, slice):
            values = self._values if self._is_sorted else sorted(self._values)

            if index.start is None and index.stop is None:
                return values[:]

            v_start = int(values[0]) if index.start is None else int(index.start)
            v_stop = (values[-1] + 1) if index.stop is None else int(index.stop)

            if v_start > v_stop or v_start > values[-1] or v_stop <= values[0]:
                return []

            if v_start <= values[0] and v_stop > values[-1]:
                return values[:]

            start_index = 0
            stop_index = len(values)

            for i, value in enumerate(values):
                if value < v_start:
                    start_index = i + 1
                elif index.stop is None:
                    break
                if value >= v_stop:
                    stop_index = i
                    break

            return values[start_index:stop_index]

    def __setitem__(self, index, name):
        assert isinstance(index, int), type(index)
        if isinstance(name, NamedInt):
            assert int(index) == int(name), repr(index) + " " + repr(name)
            value = name
        elif isinstance(name, str):
            value = NamedInt(index, name)
        else:
            raise TypeError("name must be a string")

        if str(value) in self.__dict__:
            raise ValueError(f"{value} ({int(value)}) already known")
        if int(value) in self._indexed:
            raise ValueError(f"{int(value)} ({value}) already known")

        self._values.append(value)
        self._is_sorted = False
        self._sort_values()
        self.__dict__[str(value)] = value
        self._indexed[int(value)] = value

    def __contains__(self, value):
        if isinstance(value, NamedInt):
            return self[value] == value
        elif isinstance(value, int):
            return value in self._indexed
        elif isinstance(value, str):
            return value in self.__dict__ or value in self._values

    def __iter__(self):
        yield from self._values

    def __len__(self):
        return len(self._values)

    def __repr__(self):
        return f"NamedInts({', '.join(repr(v) for v in self._values)})"

    def __or__(self, other):
        return NamedInts(**self.__dict__, **other.__dict__)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self._values == other._values


def flag_names(enum_class: Iterable, value: int) -> Generator[str]:
    """Extracts single bit flags from a (binary) number.

    Parameters
    ----------
    enum_class
        Enum class to extract flags from.
    value
        Number to extract binary flags from.
    """
    indexed = {item.value: item.name for item in enum_class}

    unknown_bits = value
    for k in indexed:
        # Ensure that the key (flag value) is a power of 2 (a single bit flag)
        assert bin(k).count("1") == 1
        if k & value == k:
            unknown_bits &= ~k
            yield indexed[k].lower()

    # Yield any remaining unknown bits
    if unknown_bits != 0:
        yield f"unknown:{unknown_bits:06X}"


class UnsortedNamedInts(NamedInts):
    def _sort_values(self):
        pass

    def __or__(self, other):
        c = UnsortedNamedInts if isinstance(other, UnsortedNamedInts) else NamedInts
        return c(**self.__dict__, **other.__dict__)


def strhex(x):
    assert x is not None
    """Produce a hex-string representation of a sequence of bytes."""
    return binascii.hexlify(x).decode("ascii").upper()


def bytes2int(x, signed=False):
    return int.from_bytes(x, signed=signed, byteorder="big")


def int2bytes(x, count=None, signed=False):
    if count:
        return x.to_bytes(length=count, byteorder="big", signed=signed)
    else:
        return x.to_bytes(length=8, byteorder="big", signed=signed).lstrip(b"\x00")


class KwException(Exception):
    """An exception that remembers all arguments passed to the constructor.
    They can be later accessed by simple member access.
    """

    def __init__(self, **kwargs):
        super().__init__(kwargs)

    def __getattr__(self, k):
        try:
            return super().__getattr__(k)
        except AttributeError:
            return self.args[0].get(k)  # was self.args[0][k]


class FirmwareKind(IntEnum):
    Firmware = 0x00
    Bootloader = 0x01
    Hardware = 0x02
    Other = 0x03


@dataclasses.dataclass
class FirmwareInfo:
    kind: FirmwareKind
    name: str
    version: str
    extras: str | None


class BatteryStatus(Flag):
    DISCHARGING = 0x00
    RECHARGING = 0x01
    ALMOST_FULL = 0x02
    FULL = 0x03
    SLOW_RECHARGE = 0x04
    INVALID_BATTERY = 0x05
    THERMAL_ERROR = 0x06


class BatteryLevelApproximation(IntEnum):
    EMPTY = 0
    CRITICAL = 5
    LOW = 20
    GOOD = 50
    FULL = 90


@dataclasses.dataclass
class Battery:
    """Information about the current state of a battery"""

    ATTENTION_LEVEL = 5

    level: Optional[Union[BatteryLevelApproximation, int]]
    next_level: Optional[Union[NamedInt, int]]
    status: Optional[BatteryStatus]
    voltage: Optional[int]
    light_level: Optional[int] = None  # light level for devices with solaar recharging

    def __post_init__(self):
        if self.level is None:  # infer level from status if needed and possible
            if self.status == BatteryStatus.FULL:
                self.level = BatteryLevelApproximation.FULL
            elif self.status in (BatteryStatus.ALMOST_FULL, BatteryStatus.RECHARGING):
                self.level = BatteryLevelApproximation.GOOD
            elif self.status == BatteryStatus.SLOW_RECHARGE:
                self.level = BatteryLevelApproximation.LOW

    def ok(self) -> bool:
        return self.status not in (BatteryStatus.INVALID_BATTERY, BatteryStatus.THERMAL_ERROR) and (
            self.level is None or self.level > Battery.ATTENTION_LEVEL
        )

    def charging(self) -> bool:
        return self.status in (
            BatteryStatus.RECHARGING,
            BatteryStatus.ALMOST_FULL,
            BatteryStatus.FULL,
            BatteryStatus.SLOW_RECHARGE,
        )

    def to_str(self) -> str:
        if isinstance(self.level, BatteryLevelApproximation):
            level = self.level.name.lower()
            status = self.status.name.lower().replace("_", " ") if self.status is not None else "Unknown"
            return _("Battery: %(level)s (%(status)s)") % {"level": _(level), "status": _(status)}
        elif isinstance(self.level, int):
            status = self.status.name.lower().replace("_", " ") if self.status is not None else "Unknown"
            return _("Battery: %(percent)d%% (%(status)s)") % {"percent": self.level, "status": _(status)}
        return ""


class Alert(IntEnum):
    NONE = 0x00
    NOTIFICATION = 0x01
    SHOW_WINDOW = 0x02
    ATTENTION = 0x04
    ALL = 0xFF


class Notification(IntEnum):
    NO_OPERATION = 0x00
    CONNECT_DISCONNECT = 0x40
    DJ_PAIRING = 0x41
    CONNECTED = 0x42
    RAW_INPUT = 0x49
    PAIRING_LOCK = 0x4A
    POWER = 0x4B


class BusID(IntEnum):
    USB = 0x03
    BLUETOOTH = 0x05
