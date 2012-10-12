#
# Some common functions and types.
#

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


from collections import namedtuple

"""Tuple returned by list_devices and find_device_by_name."""
AttachedDeviceInfo = namedtuple('AttachedDeviceInfo', [
				'handle',
				'number',
				'type',
				'name',
				'features'])

"""Firmware information."""
FirmwareInfo = namedtuple('FirmwareInfo', [
				'level',
				'type',
				'name',
				'version',
				'build',
				'extras'])

"""Reprogrammable keys informations."""
ReprogrammableKeyInfo = namedtuple('ReprogrammableKeyInfo', [
				'index',
				'id',
				'name',
				'task',
				'task_name',
				'flags'])

del namedtuple
