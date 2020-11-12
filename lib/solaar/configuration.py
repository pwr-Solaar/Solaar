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

from json import dump as _json_save
from json import load as _json_load
from logging import DEBUG as _DEBUG
from logging import INFO as _INFO
from logging import getLogger

from solaar import __version__

_log = getLogger(__name__)
del getLogger

_XDG_CONFIG_HOME = _os.environ.get('XDG_CONFIG_HOME') or _path.expanduser(_path.join('~', '.config'))
_file_path = _path.join(_XDG_CONFIG_HOME, 'solaar', 'config.json')

_KEY_VERSION = '_version'
_KEY_NAME = '_name'
_KEY_MODEL_ID = '_modelId'
_KEY_UNIT_ID = '_unitId'
_configuration = {}


def _load():
    if _path.isfile(_file_path):
        loaded_configuration = {}
        try:
            with open(_file_path, 'r') as config_file:
                loaded_configuration = _json_load(config_file)
        except Exception:
            _log.error('failed to load from %s', _file_path)

        # loaded_configuration.update(_configuration)
        _configuration.clear()
        _configuration.update(loaded_configuration)

    if _log.isEnabledFor(_DEBUG):
        _log.debug('load => %s', _configuration)

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
        except Exception:
            _log.error('failed to create %s', dirname)
            return False

    _cleanup(_configuration)

    try:
        with open(_file_path, 'w') as config_file:
            _json_save(_configuration, config_file, skipkeys=True, indent=2, sort_keys=True)

        if _log.isEnabledFor(_INFO):
            _log.info('saved %s to %s', _configuration, _file_path)
        return True
    except Exception as e:
        _log.error('failed to save to %s: %s', _file_path, e)


def _cleanup(d):
    # remove None values from the dict
    for key in list(d.keys()):
        value = d.get(key)
        if value is None:
            del d[key]
        elif isinstance(value, dict):
            _cleanup(value)


class _DeviceEntry(dict):
    def __init__(self, device, **kwargs):
        super(_DeviceEntry, self).__init__(**kwargs)
        if self.get(_KEY_NAME) != device.name:
            self[_KEY_NAME] = device.name
        self.update(device)

    def __setitem__(self, key, value):
        super(_DeviceEntry, self).__setitem__(key, value)
        save()

    def update(self, device):
        if device.modelId and device.modelId != self.get(_KEY_MODEL_ID):
            self[_KEY_MODEL_ID] = device.modelId
        if device.unitId and device.unitId != self.get(_KEY_UNIT_ID):
            self[_KEY_UNIT_ID] = device.unitId

    def get_sensitivity(self, name):
        return self.get('_sensitive', {}).get(name, False)

    def set_sensitivity(self, name, value):
        sensitives = self.get('_sensitive', {})
        if sensitives.get(name) != value:
            sensitives[name] = value
            self['_sensitive'] = sensitives


def persister(device):
    if not _configuration:
        _load()

    entry = {}
    key = None
    if device.wpid:  # connected via receiver
        entry = _configuration.get('%s:%s' % (device.wpid, device.serial), {})
    if entry or device.protocol == 1.0:  # found entry or create entry for old-style devices
        key = '%s:%s' % (device.wpid, device.serial)
    elif not entry and device.modelId:  # online new-style device so look for modelId and unitId
        for k, c in _configuration.items():
            if isinstance(c, dict) and c.get(_KEY_MODEL_ID) == device.modelId and c.get(_KEY_UNIT_ID) == device.unitId:
                entry = c  # use the entry that matches modelId and unitId
                key = k
                break
        if device.wpid and entry:  # move entry to wpid:serial
            del _configuration[key]
            key = '%s:%s' % (device.wpid, device.serial)
            _configuration[key] = entry
        elif device.wpid and not entry:  # create now with wpid:serial
            key = '%s:%s' % (device.wpid, device.serial)
        elif not entry:  # create now with modelId:unitId
            key = '%s:%s' % (device.modelId, device.unitId)
    else:  # defer until more is known (i.e., device comes on line)
        return

    if key and not isinstance(entry, _DeviceEntry):
        entry = _DeviceEntry(device, **entry)
        _configuration[key] = entry

    return entry


def attach_to(device):
    pass
