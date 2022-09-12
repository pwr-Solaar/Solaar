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

# Some common functions and types.

from binascii import hexlify as _hexlify
from collections import namedtuple

is_string = lambda d: isinstance(d, str)

#
#
#


class NamedInt(int):
    """A regular Python integer with an attached name.

    Caution: comparison with strings will also match this NamedInt's name
    (case-insensitive)."""
    def __new__(cls, value, name):
        assert is_string(name)
        obj = int.__new__(cls, value)
        obj.name = str(name)
        return obj

    def bytes(self, count=2):
        return int2bytes(self, count)

    def __eq__(self, other):
        if isinstance(other, NamedInt):
            return int(self) == int(other) and self.name == other.name
        if isinstance(other, int):
            return int(self) == int(other)
        if is_string(other):
            return self.name.lower() == other.lower()
        # this should catch comparisons with bytes in Py3
        if other is not None:
            raise TypeError('Unsupported type ' + str(type(other)))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return int(self)

    def __str__(self):
        return self.name

    def __repr__(self):
        return 'NamedInt(%d, %r)' % (int(self), self.name)


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
    __slots__ = ('__dict__', '_values', '_indexed', '_fallback', '_is_sorted')

    def __init__(self, dict=None, **kwargs):
        def _readable_name(n):
            if not is_string(n):
                raise TypeError('expected string, got ' + str(type(n)))
            return n.replace('__', '/').replace('_', ' ')

        # print (repr(kwargs))
        elements = dict if dict else kwargs
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
            assert bin(k).count('1') == 1
            if k & value == k:
                unknown_bits &= ~k
                yield str(self._indexed[k])

        if unknown_bits:
            yield 'unknown:%06X' % unknown_bits

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

        elif is_string(index):
            if index in self.__dict__:
                return self.__dict__[index]
            return (next((x for x in self._values if str(x) == index), None))

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
            assert int(index) == int(name), repr(index) + ' ' + repr(name)
            value = name
        elif is_string(name):
            value = NamedInt(index, name)
        else:
            raise TypeError('name must be a string')

        if str(value) in self.__dict__:
            raise ValueError('%s (%d) already known' % (value, int(value)))
        if int(value) in self._indexed:
            raise ValueError('%d (%s) already known' % (int(value), value))

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
        elif is_string(value):
            return value in self.__dict__ or value in self._values

    def __iter__(self):
        yield from self._values

    def __len__(self):
        return len(self._values)

    def __repr__(self):
        return 'NamedInts(%s)' % ', '.join(repr(v) for v in self._values)

    def __or__(self, other):
        return NamedInts(**self.__dict__, **other.__dict__)


class UnsortedNamedInts(NamedInts):
    def _sort_values(self):
        pass

    def __or__(self, other):
        c = UnsortedNamedInts if isinstance(other, UnsortedNamedInts) else NamedInts
        return c(**self.__dict__, **other.__dict__)


def strhex(x):
    assert x is not None
    """Produce a hex-string representation of a sequence of bytes."""
    return _hexlify(x).decode('ascii').upper()


def bytes2int(x, signed=False):
    return int.from_bytes(x, signed=signed, byteorder='big')


def int2bytes(x, count=None, signed=False):
    if count:
        return x.to_bytes(length=count, byteorder='big', signed=signed)
    else:
        return x.to_bytes(length=8, byteorder='big', signed=signed).lstrip(b'\x00')


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
            return self.args[0][k]


"""Firmware information."""
FirmwareInfo = namedtuple('FirmwareInfo', ['kind', 'name', 'version', 'extras'])

BATTERY_APPROX = NamedInts(empty=0, critical=5, low=20, good=50, full=90)

del namedtuple
