# -*- python-mode -*-
# -*- coding: UTF-8 -*-

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

import os as _os
import os.path as _path
from json import load as _json_load, dump as _json_save

from logging import getLogger, DEBUG as _DEBUG, INFO as _INFO
_log = getLogger(__name__)
del getLogger

_XDG_CONFIG_HOME = _os.environ.get('XDG_CONFIG_HOME') or _path.expanduser(_path.join('~', '.config'))
_file_path = _path.join(_XDG_CONFIG_HOME, 'solaar', 'config.json')


from solaar import __version__
_KEY_VERSION = '_version'
_KEY_NAME = '_name'
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

	_cleanup(_configuration)
	_configuration[_KEY_VERSION] = __version__
	return _configuration


def save():
	# don't save if the configuration hasn't been loaded
	if _KEY_VERSION not in _configuration:
		return

	dirname = _os.path.dirname(_file_path)
	if not _path.isdir(dirname):
		try:
			_os.makedirs(dirname)
		except:
			_log.error("failed to create %s", dirname)
			return False

	_cleanup(_configuration)

	try:
		with open(_file_path, 'w') as config_file:
			_json_save(_configuration, config_file, skipkeys=True, indent=2, sort_keys=True)

		if _log.isEnabledFor(_INFO):
			_log.info("saved %s to %s", _configuration, _file_path)
		return True
	except:
		_log.error("failed to save to %s", _file_path)


def _cleanup(d):
	# remove None values from the dict
	for key in list(d.keys()):
		value = d.get(key)
		if value is None:
			del d[key]
		elif isinstance(value, dict):
			_cleanup(value)


def _device_key(device):
	return '%s:%s' % (device.wpid, device.serial)


class _DeviceEntry(dict):
	def __init__(self, *args, **kwargs):
		super(_DeviceEntry, self).__init__(*args, **kwargs)

	def __setitem__(self, key, value):
		super(_DeviceEntry, self).__setitem__(key, value)
		save()


def _device_entry(device):
	if not _configuration:
		_load()

	device_key = _device_key(device)
	c = _configuration.get(device_key) or {}

	if not isinstance(c, _DeviceEntry):
		c[_KEY_NAME] = device.name
		c = _DeviceEntry(c)
		_configuration[device_key] = c

	return c


def attach_to(device):
	"""Apply the last saved configuration to a device."""
	if not _configuration:
		_load()

	persister = _device_entry(device)
	device.persister = persister
