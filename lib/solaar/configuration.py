#
#
#

import os as _os
import os.path as _path
from json import load as _json_load, dump as _json_save

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger(__name__)
del getLogger

_XDG_CONFIG_HOME = _os.environ.get('XDG_CONFIG_HOME') or _path.join(_path.expanduser('~'), '.config')
_file_path = _path.join(_path.join(_XDG_CONFIG_HOME, 'solaar'), 'config.json')


from solaar import __version__
_configuration = {}


def _load():
	if _path.isfile(_file_path):
		loaded_configuration = {}
		try:
			with open(_file_path, 'r') as config_file:
				loaded_configuration = _json_load(config_file)
		except:
			_log.error("failed to load from %s", _file_path)

		# loaded_configuration.update(_configuration)
		_configuration.clear()
		_configuration.update(loaded_configuration)

	if _log.isEnabledFor(_DEBUG):
		_log.debug("load => %s", _configuration)

	_configuration['_version'] = __version__
	return _configuration


def save():
	dirname = _os.path.dirname(_file_path)
	if not _path.isdir(dirname):
		try:
			_os.makedirs(dirname)
		except:
			_log.error("failed to create %s", dirname)
			return False

	try:
		with open(_file_path, 'w') as config_file:
			_json_save(_configuration, config_file, skipkeys=True, indent=2, sort_keys=True)

		_log.info("saved %s to %s", _configuration, _file_path)
		return True
	except:
		_log.error("failed to save to %s", _file_path)


def all():
	if not _configuration:
		_load()

	return dict(_configuration)


def _device_key(device):
	return '%s:%s' % (device.serial, device.kind)


def _device_entry(device):
	if not _configuration:
		_load()

	device_key = _device_key(device)
	if device_key in _configuration:
		c = _configuration[device_key]
	else:
		c = _configuration[device_key] = {}

	c['_name'] = device.name
	return c


def attach_to(device):
	"""Apply the last saved configuration to a device."""
	if not _configuration:
		_load()

	persister = _device_entry(device)
	for s in device.settings:
		if s.persister is None:
			s.persister = persister
		assert s.persister == persister
		if s.name in persister:
			s.write(persister[s.name])
		else:
			persister[s.name] = s.read(cached=False)
