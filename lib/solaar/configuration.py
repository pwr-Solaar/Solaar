# -*- python-mode -*-

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

import json as _json
import os as _os
import os.path as _path

from logging import DEBUG as _DEBUG
from logging import INFO as _INFO
from logging import getLogger

import yaml as _yaml

from logitech_receiver.common import NamedInt as _NamedInt
from solaar import __version__

_log = getLogger(__name__)
del getLogger

_XDG_CONFIG_HOME = _os.environ.get('XDG_CONFIG_HOME') or _path.expanduser(_path.join('~', '.config'))
_file_path = _path.join(_XDG_CONFIG_HOME, 'solaar', 'config.json')
_yaml_file_path = _path.join(_XDG_CONFIG_HOME, 'solaar', 'config.yaml')

_KEY_VERSION = '_version'
_KEY_NAME = '_NAME'
_KEY_WPID = '_wpid'
_KEY_SERIAL = '_serial'
_KEY_MODEL_ID = '_modelId'
_KEY_UNIT_ID = '_unitId'
_KEY_ABSENT = '_absent'
_KEY_SENSITIVE = '_sensitive'
_config = []


def _load():
    global _config
    loaded_config = []
    if _path.isfile(_yaml_file_path):
        try:
            with open(_yaml_file_path) as config_file:
                loaded_config = _yaml.safe_load(config_file)
        except Exception as e:
            _log.error('failed to load from %s: %s', _yaml_file_path, e)
    elif _path.isfile(_file_path):
        try:
            with open(_file_path) as config_file:
                loaded_config = _json.load(config_file)
        except Exception as e:
            _log.error('failed to load from %s: %s', _file_path, e)
        loaded_config = _convert_json(loaded_config)
    if _log.isEnabledFor(_DEBUG):
        _log.debug('load => %s', loaded_config)
    _config = _cleanup_load(loaded_config)


def save():
    if not _config:
        return
    dirname = _os.path.dirname(_yaml_file_path)
    if not _path.isdir(dirname):
        try:
            _os.makedirs(dirname)
        except Exception:
            _log.error('failed to create %s', dirname)
            return False

    try:
        with open(_yaml_file_path, 'w') as config_file:
            _yaml.dump(_config, config_file, default_flow_style=None, width=150)

        if _log.isEnabledFor(_INFO):
            _log.info('saved %s to %s', _config, _yaml_file_path)
        return True
    except Exception as e:
        _log.error('failed to save to %s: %s', _yaml_file_path, e)


def _convert_json(json_dict):
    config = [json_dict.get(_KEY_VERSION)]
    for key, dev in json_dict.items():
        key = key.split(':')
        if len(key) == 2:
            dev[_KEY_WPID] = dev.get(_KEY_WPID) if dev.get(_KEY_WPID) else key[0]
            dev[_KEY_SERIAL] = dev.get(_KEY_SERIAL) if dev.get(_KEY_SERIAL) else key[1]
            for k, v in dev.items():
                if type(k) == str and not k.startswith('_') and type(v) == dict:  # convert string keys to ints
                    v = {int(dk) if type(dk) == str else dk: dv for dk, dv in v.items()}
                dev[k] = v
            for k in ['mouse-gestures', 'dpi-sliding']:
                v = dev.get(k, None)
                if v is True or v is False:
                    dev.pop(k)
            if '_name' in dev:
                dev[_KEY_NAME] = dev['_name']
                dev.pop('_name')
            config.append(dev)
    return config


def _cleanup_load(c):
    _config = [__version__]
    for element in c:
        if isinstance(element, dict):
            # convert to device entries
            element = _DeviceEntry(**element)
            _config.append(element)
    return _config


class _DeviceEntry(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        save()

    def update(self, device):
        if device.name and device.name != self.get(_KEY_NAME):
            super().__setitem__(_KEY_NAME, device.name)
        if device.wpid and device.wpid != self.get(_KEY_WPID):
            super().__setitem__(_KEY_WPID, device.wpid)
        if device.serial and device.serial != '?' and device.serial != self.get(_KEY_SERIAL):
            super().__setitem__(_KEY_SERIAL, device.serial)
        if device.modelId and device.modelId != self.get(_KEY_MODEL_ID):
            super().__setitem__(_KEY_MODEL_ID, device.modelId)
        if device.unitId and device.unitId != self.get(_KEY_UNIT_ID):
            super().__setitem__(_KEY_UNIT_ID, device.unitId)

    def get_sensitivity(self, name):
        return self.get(_KEY_SENSITIVE, {}).get(name, False)

    def set_sensitivity(self, name, value):
        sensitives = self.get(_KEY_SENSITIVE, {})
        if sensitives.get(name) != value:
            sensitives[name] = value
            self.__setitem__(_KEY_SENSITIVE, sensitives)


def device_representer(dumper, data):
    return dumper.represent_mapping('tag:yaml.org,2002:map', data)


_yaml.add_representer(_DeviceEntry, device_representer)


def named_int_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:int', str(int(data)))


_yaml.add_representer(_NamedInt, named_int_representer)


# A device can be identified by a combination of WPID and serial number (for receiver-connected devices)
# or a combination of modelId and unitId (for direct-connected devices).
# The worst situation is a receiver-connected device that Solaar has never seen on-line
# that is directly connected.  Here there is no way to realize that the two devices are the same.
# So new entries are not created for unseen off-line receiver-connected devices except for those with protocol 1.0
def persister(device):
    def match(wpid, serial, modelId, unitId, c):
        return ((wpid and wpid == c.get(_KEY_WPID) and serial and serial == c.get(_KEY_SERIAL)) or (
            modelId and modelId != '000000000000' and modelId == c.get(_KEY_MODEL_ID) and unitId
            and unitId == c.get(_KEY_UNIT_ID)
        ))

    if not _config:
        _load()
    entry = None
    for c in _config:
        if isinstance(c, _DeviceEntry) and match(device.wpid, device.serial, device.modelId, device.unitId, c):
            entry = c
            break
    if not entry:
        if not device.online and not device.serial:  # don't create entry for offline devices without serial number
            if _log.isEnabledFor(_INFO):
                _log.info('not setting up persister for offline device %s with missing serial number', device.name)
            return
        entry = _DeviceEntry()
        _config.append(entry)
    entry.update(device)
    return entry


def attach_to(device):
    pass
