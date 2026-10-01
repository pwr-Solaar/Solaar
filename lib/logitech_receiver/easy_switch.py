## Copyright (C) 2026  Solaar Contributors https://pwr-solaar.github.io/Solaar/
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

"""Enhanced Easy-Switch: devices linked to a keyboard change hosts along with the keyboard.

Logi Options+ links a device, usually a mouse, to a keyboard by setting all host cookies of the device to the
easy_switch_cookie of the keyboard.  When its Easy-Switch keys change the host, a keyboard with CHANGE_HOST version 2
or later sends a notification with its current and its new host, and disconnects right after that.  The program on the
computer that the keyboard leaves then switches each linked device to the paired host that has the same name
(HOSTS_INFO) as the new host of the keyboard.  This is what Logi Options+ does, so it works with Logi Options+ on
the other computers, as long as each computer has its own name.
"""

from __future__ import annotations

import logging
import time

from dataclasses import dataclass
from dataclasses import field
from typing import Optional

from . import hidpp20
from .hidpp20_constants import SupportedFeature

logger = logging.getLogger(__name__)

_hidpp20 = hidpp20.Hidpp20()

DEADLINE = 3.0  # seconds after the notification after which linked devices are not switched any more


@dataclass(frozen=True)
class Hosts:
    """What is known about the hosts of a device, read when the device connected."""

    names: dict = field(default_factory=dict)  # host index -> (paired, name)
    cookies: bytes = b""  # host cookies of a device that can be linked to a keyboard
    link_cookie: Optional[int] = None  # host cookie of the devices linked to a keyboard


def read_hosts(device, host_names) -> Hosts:
    """Reads what is needed about the hosts of a device that can change hosts, given the names of its hosts."""
    version = device.features.get_feature_version(SupportedFeature.CHANGE_HOST) or 0
    if str(device.kind) == "keyboard":
        return Hosts(host_names, link_cookie=hidpp20.easy_switch_cookie(device.unitId) if version >= 2 else None)
    info = _hidpp20.get_change_host_info(device) if version >= 1 else None
    cookies = _hidpp20.get_host_cookies(device, info[0]) if info else None
    return Hosts(host_names, cookies=cookies or b"")


def handler(device, n):
    """Notification handler for keyboards that makes the devices linked to the keyboard follow it to its new host."""
    try:
        if (
            n.sub_id < 0x40
            and n.address == 0x00
            and len(n.data) >= 2
            and n.data[0] != n.data[1]
            and device.features.get_feature(n.sub_id) == SupportedFeature.CHANGE_HOST
        ):
            from . import device as _device  # imported here as device imports settings_templates, which imports this

            # the keyboard is leaving, so what is known about its hosts is not used or updated until it connects again
            hosts, device.hosts = device.hosts, None
            follow(device, hosts, n.data[1], list(_device.Device.instances))
    except Exception as e:
        logger.warning("%s: error in Enhanced Easy-Switch: %r", device, e)
    return None  # other handlers and rules also get the notification


def follow(keyboard, hosts, new_host, devices):
    """Switches the devices linked to the keyboard to the host with the name of the new host of the keyboard.

    The keyboard is about to disconnect, so only what was read when it connected (hosts) is used and nothing is sent
    to the keyboard.
    """
    paired, name = hosts.names.get(new_host, (False, "")) if hosts else (False, "")
    if not paired or not name:
        logger.info("%s: name of host %d is not known, so linked devices stay", keyboard, new_host + 1)
        return
    if not hosts.link_cookie:  # unlinked devices have cookie 0
        logger.info("%s: no host cookie for linked devices, so linked devices stay", keyboard)
        return
    start = time.monotonic()
    for device in devices:
        device_hosts = getattr(device, "hosts", None)
        # only ask devices that were linked to the keyboard when they connected
        if device is not keyboard and device.online and device_hosts and hosts.link_cookie in device_hosts.cookies:
            if time.monotonic() - start > DEADLINE:
                logger.warning("%s: too late to follow %s", device, keyboard)
                continue
            try:
                _switch(device, device_hosts, keyboard, hosts.link_cookie, name, new_host, start)
            except Exception as e:
                logger.warning("%s: error following %s: %r", device, keyboard, e)


def _switch(device, device_hosts, keyboard, link_cookie, name, new_host, start):
    info = _hidpp20.get_change_host_info(device)
    cookies = _hidpp20.get_host_cookies(device, info[0]) if info else None
    if not cookies:
        logger.info("%s: does not respond, so it does not follow %s", device, keyboard)
        return
    current_host = info[1]
    if current_host >= len(cookies) or cookies[current_host] != link_cookie:
        logger.info("%s: not linked to %s on host %d, so it does not follow", device, keyboard, current_host + 1)
        return
    # the keyboard is leaving the current host of the device, so that host is never the one to switch to
    names = {host: host_name for host, host_name in device_hosts.names.items() if host != current_host}
    host = choose_host(device, names, name, new_host)
    if host is None:
        logger.info("%s: no other paired host is named %r, so it does not follow %s", device, name, keyboard)
    elif time.monotonic() - start > DEADLINE:
        logger.warning("%s: too late to follow %s", device, keyboard)
    else:
        logger.info("%s: follow %s from host %d to host %d (%s)", device, keyboard, current_host + 1, host + 1, name)
        _hidpp20.set_current_host(device, host)


def choose_host(device, host_names, name, preferred):
    """Returns the paired host of the device with this name, the preferred host if several have the name, or None."""
    hosts = [host for host, (paired, host_name) in sorted(host_names.items()) if paired and host_name == name]
    if len(hosts) > 1:
        logger.warning("%s: hosts %s all have name %r", device, [host + 1 for host in hosts], name)
    return preferred if preferred in hosts else next(iter(hosts), None)
