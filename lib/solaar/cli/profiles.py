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

import traceback

import yaml

from logitech_receiver.hidpp20 import OnboardProfiles
from logitech_receiver.hidpp20 import OnboardProfilesVersion


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
        raise Exception(f"no online device found matching '{device_name}'")

    if not (dev.online and dev.profiles):
        print(f"Device {dev.name} is either offline or has no onboard profiles")
    elif not profiles_file:
        print(f"#Dumping profiles from {dev.name}")
        print(yaml.dump(dev.profiles))
    else:
        try:
            with open(profiles_file, "r") as f:
                print(f"Reading profiles from {profiles_file}")
                profiles = yaml.safe_load(f)
                if not isinstance(profiles, OnboardProfiles):
                    print("Profiles file does not contain current onboard profiles")
                elif getattr(profiles, "version", None) != OnboardProfilesVersion:
                    version = getattr(profiles, "version", None)
                    print(f"Missing or incorrect profile version {version} in loaded profile")
                elif getattr(profiles, "name", None) != dev.name:
                    name = getattr(profiles, "name", None)
                    print(f"Different device name {name} in loaded profile")
                else:
                    print(f"Loading profiles into {dev.name}")
                    written = profiles.write(dev)
                    print(f"Wrote {written} sectors to {dev.name}")
        except Exception as exc:
            print("Profiles not written:", exc)
            print(traceback.format_exc())
