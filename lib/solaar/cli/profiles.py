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

import traceback as _traceback

import yaml as _yaml

from logitech_receiver.hidpp20 import OnboardProfiles as _OnboardProfiles


def run(receivers, args, find_receiver, find_device):
    assert receivers
    assert args.device

    device_name = args.device.lower()
    profiles_file = args.profiles

    dev = None
    for dev in find_device(receivers, device_name):
        if dev.ping():
            break
        dev = None

    if not dev:
        raise Exception("no online device found matching '%s'" % device_name)

    if not (dev.online and dev.profiles):
        print(f'Device {dev.name} is either offline or has no onboard profiles')
    elif not profiles_file:
        print(f'#Dumping profiles from {dev.name}')
        print(_yaml.dump(dev.profiles))
    else:
        try:
            with open(profiles_file, 'r') as f:
                print(f'Reading profiles from {profiles_file}')
                profiles = _yaml.safe_load(f)
                if not isinstance(profiles, _OnboardProfiles):
                    print('Profiles file does not contain onboard profiles')
                else:
                    print(f'Loading profiles into {dev.name}')
                    written = profiles.write(dev)
                    print(f'Wrote {written} sectors to {dev.name}')
        except Exception as exc:
            print('Profiles not written:', exc)
            print(_traceback.format_exc())
