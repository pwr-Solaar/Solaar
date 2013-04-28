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
		assert isinstance(name, str) or isinstance(name, unicode)
		obj = int.__new__(cls, value)
		obj.name = unicode(name)
		return obj

	def bytes(self, count=2):
		if self.bit_length() > count * 8:
			raise ValueError('cannot fit %X into %d bytes' % (self, count))
		return _pack(b'!L', self)[-count:]

	def __eq__(self, other):
		if isinstance(other, NamedInt):
			return int(self) == int(other) and self.name == other.name
		if isinstance(other, int):
			return int(self) == int(other)
		if isinstance(other, str) or isinstance(other, unicode):
			return self.name.lower() == other.lower()

	def __ne__(self, other):
		return not self.__eq__(other)

	def __hash__(self):
		return int(self)

	def __str__(self):
		return self.name
	__unicode__ = __str__

	def __repr__(self):
		return 'NamedInt(%d, %r)' % (int(self), self.name)


class NamedInts(object):
	"""An ordered set of NamedInt values.

	Indexing can be made by int or string, and will return the corresponding
	NamedInt if it exists in this set, or `None`.

	Extracting slices will return all present NamedInts in the given interval
	(extended slices are not supported).

	Assigning a string to an indexed int will create a new NamedInt in this set;
	if the value already exists in the set (int or string), ValueError will be
	raised.
	"""
	__slots__ = ['__dict__', '_values', '_indexed', '_fallback']

	def __init__(self, **kwargs):
		def _readable_name(n):
			if not isinstance(n, str) and not isinstance(n, unicode):
				raise TypeError("expected string, got " + type(n))
			return n.replace('__', '/').replace('_', ' ')

		values = {k: NamedInt(v, _readable_name(k)) for (k, v) in kwargs.items()}
		self.__dict__ = values
		self._values = sorted(list(values.values()))
		self._indexed = {int(v): v for v in self._values}
		self._fallback = None

	@classmethod
	def range(cls, from_value, to_value, name_generator=lambda x: str(x), step=1):
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

	def __getitem__(self, index):
		if isinstance(index, int):
			if index in self._indexed:
				return self._indexed[int(index)]
			if self._fallback and type(index) == int:
				value = NamedInt(index, self._fallback(index))
				self._indexed[index] = value
				self._values = sorted(self._values + [value])
				return value

		elif isinstance(index, str) or isinstance(index, unicode):
			if index in self.__dict__:
				return self.__dict__[index]

		elif isinstance(index, slice):
			if index.start is None and index.stop is None:
				return self._values[:]

			v_start = int(self._values[0]) if index.start is None else int(index.start)
			v_stop = (self._values[-1] + 1) if index.stop is None else int(index.stop)

			if v_start > v_stop or v_start > self._values[-1] or v_stop <= self._values[0]:
				return []

			if v_start <= self._values[0] and v_stop > self._values[-1]:
				return self._values[:]

			start_index = 0
			stop_index = len(self._values)
			for i, value in enumerate(self._values):
				if value < v_start:
					start_index = i + 1
				elif index.stop is None:
					break
				if value >= v_stop:
					stop_index = i
					break

			return self._values[start_index:stop_index]

	def __setitem__(self, index, name):
		assert isinstance(index, int), type(index)
		if isinstance(name, NamedInt):
			assert int(index) == int(name), repr(index) + ' ' + repr(name)
			value = name
		elif isinstance(name, str) or isinstance(name, unicode):
			value = NamedInt(index, name)
		else:
			raise TypeError('name must be a string')

		if str(value) in self.__dict__:
			raise ValueError('%s (%d) already known' % (value, int(value)))
		if int(value) in self._indexed:
			raise ValueError('%d (%s) already known' % (int(value), value))

		self._values = sorted(self._values + [value])
		self.__dict__[str(value)] = value
		self._indexed[int(value)] = value

	def __contains__(self, value):
		if isinstance(value, int):
			return value in self._indexed
		if isinstance(value, str) or isinstance(value, unicode):
			return value in self.__dict__

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
