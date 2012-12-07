#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from weakref import proxy as _proxy
from copy import copy as _copy

from .common import NamedInts as _NamedInts

#
#
#

KIND = _NamedInts(toggle=0x1, choice=0x02, range=0x03)

class Setting(object):
	__slots__ = ['name', 'kind', 'label', 'description', 'choices', '_device', '_value', 'register']

	def __init__(self, name, kind, label, description=None, choices=None):
		self.name = name
		self.kind = kind
		self.label = label
		self.description = description
		self.choices = choices
		self.register = None

	def __call__(self, device):
		o = _copy(self)
		o._value = None
		o._device = _proxy(device)
		return o

	def read_register(self):
		return self._device.request(0x8100 | (self.register & 0x2FF))

	def write_register(self, value, value2=0):
		return self._device.request(0x8000 | (self.register & 0x2FF), int(value) & 0xFF, int(value2) & 0xFF)

	def read(self):
		raise NotImplemented

	def write(self, value):
		raise NotImplemented

	def __str__(self):
		return '<%s(%s=%s)>' % (self.__class__.__name__, self.name, self._value)
	__unicode__ = __repr__ = __str__
