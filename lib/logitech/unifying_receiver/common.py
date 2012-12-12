#
# Some common functions and types.
#

from __future__ import absolute_import, division, print_function, unicode_literals

from binascii import hexlify as _hexlify
from struct import pack as _pack


class NamedInt(int):
	"""An reqular Python integer with an attached name.

	Caution: comparison with strings will also match this NamedInt's name
	(case-insensitive)."""

	def __new__(cls, value, name):
		obj = int.__new__(cls, value)
		obj.name = str(name)
		return obj

	def bytes(self, count=2):
		value = int(self)
		if value.bit_length() > count * 8:
			raise ValueError('cannot fit %X into %d bytes' % (value, count))
		return _pack(b'!L', value)[-count:]

	def __eq__(self, other):
		if isinstance(other, NamedInt):
			return int(self) == int(other) and self.name == other.name
		if isinstance(other, int):
			return int(self) == int(other)
		if isinstance(other, basestring):
			return self.name.lower() == other.lower()

	def __ne__(self, other):
		return not self.__eq__(other)

	def __str__(self):
		return self.name
	__unicode__ = __str__

	def __repr__(self):
		return 'NamedInt(%d, %s)' % (int(self), repr(self.name))


class NamedInts(object):
	"""A collection of NamedInt values.

	Behaves partially like a sorted list (by int value), partially like a dict.
	"""
	__slots__ = ['__dict__', '_values', '_indexed', '_fallback']

	def __init__(self, **kwargs):
		def _readable_name(n):
			assert isinstance(n, basestring)
			if n == n.upper():
				n.lstrip('_')
			return n.replace('__', '/').replace('_', ' ')

		values = {k: NamedInt(v, _readable_name(k)) for (k, v) in kwargs.items()}
		self.__dict__ = values
		self._values = sorted(list(values.values()))
		self._indexed = {int(v): v for v in self._values}
		self._fallback = None

	def flag_names(self, value):
		unknown_bits = value
		for k in self._indexed:
			assert bin(k).count('1') == 1
			if k & value == k:
				unknown_bits &= ~k
				yield str(self._indexed[k])

		if unknown_bits:
			yield 'unknown:%06X' % unknown_bits

	def index(self, value):
		if value in self._values:
			return self._values.index(value)
		raise IndexError('%s not found' % value)

	def __getitem__(self, index):
		if isinstance(index, int):
			if index in self._indexed:
				return self._indexed[int(index)]
			if self._fallback and type(index) == int:
				value = NamedInt(index, self._fallback(index))
				self._indexed[index] = value
				self._values = sorted(self._values + [value])
				return value

		elif isinstance(index, slice):
			return self._values[index]

		elif isinstance(index, basestring):
			if index in self.__dict__:
				return self.__dict__[index]

	def __setitem__(self, index, name):
		assert isinstance(index, int)
		if isinstance(name, NamedInt):
			assert int(index) == int(name)
			value = name
		elif isinstance(name, basestring):
			value = NamedInt(index, name)
		else:
			raise TypeError('name must be a basestring')

		if str(value) in self.__dict__:
			raise ValueError('%s (%d) already known' % (str(value), int(value)))
		if int(value) in self._indexed:
			raise ValueError('%d (%s) already known' % (int(value), str(value)))

		self._values = sorted(self._values + [value])
		self.__dict__[str(value)] = value
		self._indexed[int(value)] = value

	def __contains__(self, value):
		if isinstance(value, int):
			return int(value) in self._indexed
		if isinstance(value, basestring):
			return str(value) in self.__dict__

	def __iter__(self):
		for v in self._values:
			yield v

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
