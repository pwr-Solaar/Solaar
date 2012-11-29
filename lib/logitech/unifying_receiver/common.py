#
# Some common functions and types.
#

from binascii import hexlify as _hexlify
from struct import pack as _pack


class NamedInt(int):
	"""An integer with an attached name."""
	# __slots__ = ['name']

	def __new__(cls, value, name):
		obj = int.__new__(cls, value)
		obj.name = name
		return obj

	def bytes(self, count=2):
		value = int(self)
		if value.bit_length() > count * 8:
			raise ValueError("cannot fit %X into %d bytes" % (value, count))

		return _pack('!L', value)[-count:]


	def __str__(self):
		return self.name

	def __repr__(self):
		return 'NamedInt(%d, %s)' % (int(self), repr(self.name))


class NamedInts(object):
	def __init__(self, **kwargs):
		values = dict((k, NamedInt(v, k if k == k.upper() else k.replace('__', '/').replace('_', ' '))) for (k, v) in kwargs.items())
		self.__dict__.update(values)
		self._indexed = dict((int(v), v) for v in values.values())
		self._fallback = None

	def __getitem__(self, index):
		if index in self._indexed:
			return self._indexed[index]

		if self._fallback:
			value = NamedInt(index, self._fallback(index))
			self._indexed[index] = value
			return value

	def __contains__(self, value):
		return int(value) in self._indexed

	def __len__(self):
		return len(self.values)

	def flag_names(self, value):
		return ', '.join(str(self._indexed[k]) for k in self._indexed if k & value == k)


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
