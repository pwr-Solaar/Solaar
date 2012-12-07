#
# Some common functions and types.
#

from __future__ import absolute_import, division, print_function, unicode_literals

from binascii import hexlify as _hexlify
from struct import pack as _pack


class NamedInt(int):
	"""An reqular Python integer with an attached name.

	Careful when using this, because
	"""

	def __new__(cls, value, name):
		obj = int.__new__(cls, value)
		obj.name = str(name)
		return obj

	def bytes(self, count=2):
		value = int(self)
		if value.bit_length() > count * 8:
			raise ValueError('cannot fit %X into %d bytes' % (value, count))

		return _pack(b'!L', value)[-count:]

	def __hash__(self):
		return int(self)

	def __eq__(self, other):
		if isinstance(other, int):
			return int(self) == int(other)

		if isinstance(other, str):
			return self.name.lower() == other.lower()

	def __ne__(self, other):
		if isinstance(other, int):
			return int(self) != int(other)

		if isinstance(other, str):
			return self.name.lower() != other.lower()

	def __lt__(self, other):
		if not isinstance(other, int):
			raise TypeError('unorderable types: %s < %s' % (type(self), type(other)))
		return int(self) < int(other)

	def __le__(self, other):
		if not isinstance(other, int):
			raise TypeError('unorderable types: %s <= %s' % (type(self), type(other)))
		return int(self) <= int(other)

	def __gt__(self, other):
		if not isinstance(other, int):
			raise TypeError('unorderable types: %s > %s' % (type(self), type(other)))
		return int(self) > int(other)

	def __ge__(self, other):
		if not isinstance(other, int):
			raise TypeError('unorderable types: %s >= %s' % (type(self), type(other)))
		return int(self) >= int(other)

	def __str__(self):
		return self.name
	__unicode__ = __str__

	def __repr__(self):
		return 'NamedInt(%d, %s)' % (int(self), repr(self.name))


class NamedInts(object):
	__slots__ = ['__dict__', '_values', '_indexed', '_fallback']

	def __init__(self, **kwargs):
		values = dict((k, NamedInt(v, k.lstrip('_') if k == k.upper() else
										k.replace('__', '/').replace('_', ' '))) for (k, v) in kwargs.items())
		self.__dict__ = values
		self._values = sorted(list(values.values()))
		self._indexed = dict((int(v), v) for v in self._values)
		self._fallback = None

	def flag_names(self, value):
		return ', '.join(str(self._indexed[k]) for k in self._indexed if k & value == k)

	def index(self, value):
		if value in self._values:
			return self._values.index(value)
		raise IndexError('%s not found' % value)

	def __getitem__(self, index):
		if type(index) == int:
			if index in self._indexed:
				return self._indexed[index]

			if self._fallback:
				value = NamedInt(index, self._fallback(index))
				self._indexed[index] = value
				self._values = sorted(self._values + [value])
				return value

		elif type(index) == slice:
			return self._values[index]

		else:
			if index in self._values:
				index = self._values.index(index)
				return self._values[index]

	def __contains__(self, value):
		return value in self._values

	def __iter__(self):
		return iter(sorted(self._values))

	def __len__(self):
		return len(self._values)

	def __repr__(self):
		return 'NamedInts(%s)' % ', '.join(repr(v) for v in self._values)


def strhex(x):
	return _hexlify(x).decode('ascii').upper()


class KwException(Exception):
	def __init__(self, **kwargs):
		super(KwException, self).__init__(kwargs)

	def __getattr__(self, k):
		try:
			return super(KwException, self).__getattr__(k)
		except AttributeError:
			return self.args[0][k]


from collections import namedtuple

"""Firmware information."""
FirmwareInfo = namedtuple('FirmwareInfo', [
				'kind',
				'name',
				'version',
				'extras'])

"""Reprogrammable keys informations."""
ReprogrammableKeyInfo = namedtuple('ReprogrammableKeyInfo', [
				'index',
				'key',
				'task',
				'flags'])

del namedtuple
