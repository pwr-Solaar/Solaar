#
# Some common functions and types.
#

from collections import namedtuple
from binascii import hexlify as _hexlify
_hex = lambda d: _hexlify(d).decode('ascii').upper()


class FallbackDict(dict):
	def __init__(self, fallback_function=lambda x: None, *args, **kwargs):
		super(FallbackDict, self).__init__(*args, **kwargs)
		self.fallback = fallback_function

	def __getitem__(self, key):
		try:
			return super(FallbackDict, self).__getitem__(key)
		except KeyError:
			return self.fallback(key)


def list2dict(values_list):
	return dict(zip(range(0, len(values_list)), values_list))


"""Firmware information."""
FirmwareInfo = namedtuple('FirmwareInfo', [
				'level',
				'kind',
				'name',
				'version',
				'extras'])

"""Reprogrammable keys informations."""
ReprogrammableKeyInfo = namedtuple('ReprogrammableKeyInfo', [
				'index',
				'id',
				'name',
				'task',
				'task_name',
				'flags'])


class Packet(namedtuple('Packet', ['code', 'devnumber', 'data'])):
	def __str__(self):
		return 'Packet(%02X,%02X,%s)' % (self.code, self.devnumber, 'None' if self.data is None else _hex(self.data))

del namedtuple
