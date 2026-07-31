## Copyright (C) 2012-2013  Daniel Pavel
## Copyright (C) 2014-2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
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
from __future__ import annotations

import logging

from typing import Callable

logger = logging.getLogger(__name__)

try:
    import dbus
    import dbus.service

    from dbus.mainloop.glib import DBusGMainLoop  # integration into the main GLib loop

    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    assert bus

except Exception:
    # Either the dbus library is not available or the system dbus is not running
    logger.warning("failed to set up dbus")
    bus = None


_suspend_callback = None
_resume_callback = None


def _suspend_or_resume(suspend):
    if suspend and _suspend_callback:
        _suspend_callback()
    if not suspend and _resume_callback:
        _resume_callback()


_LOGIND_PATH = "/org/freedesktop/login1"
_LOGIND_INTERFACE = "org.freedesktop.login1.Manager"


def watch_suspend_resume(
    on_resume_callback: Callable[[], None] | None = None,
    on_suspend_callback: Callable[[], None] | None = None,
):
    """Register callback for suspend/resume events.
    They are called only if the system DBus is running, and the Login daemon is available."""
    global _resume_callback, _suspend_callback
    _suspend_callback = on_suspend_callback
    _resume_callback = on_resume_callback
    if bus is not None and on_resume_callback is not None or on_suspend_callback is not None:
        bus.add_signal_receiver(
            _suspend_or_resume,
            "PrepareForSleep",
            dbus_interface=_LOGIND_INTERFACE,
            path=_LOGIND_PATH,
        )
    logger.info("connected to system dbus, watching for suspend/resume events")


_BLUETOOTH_PATH_PREFIX = "/org/bluez/hci0/dev_"
_BLUETOOTH_INTERFACE = "org.freedesktop.DBus.Properties"

_bluetooth_callbacks = {}


def watch_bluez_connect(serial, callback=None):
    if _bluetooth_callbacks.get(serial):
        _bluetooth_callbacks.get(serial).remove()
    path = _BLUETOOTH_PATH_PREFIX + serial.replace(":", "_").upper()
    if bus is not None and callback is not None:
        _bluetooth_callbacks[serial] = bus.add_signal_receiver(
            callback, "PropertiesChanged", path=path, dbus_interface=_BLUETOOTH_INTERFACE
        )

class BatteryBroadcaster(dbus.service.Object):
    def __init__(self, bus_name, path):
        super().__init__(bus_name, path)
        self.levels = {}
        self.charging = {}

    @dbus.service.signal('io.github.pwr_solaar.solaar.Battery', signature='sib')
    def BatteryChanged(self, serial, level, is_charging):
        pass

    @dbus.service.method('io.github.pwr_solaar.solaar.Battery', in_signature='s', out_signature='(ib)')
    def GetBattery(self, serial):
        return (self.levels.get(serial, -1), self.charging.get(serial, False))

    @dbus.service.method('io.github.pwr_solaar.solaar.Battery', in_signature='', out_signature='a{s(ib)}')
    def GetAllBatteries(self):
        return {s: (self.levels[s], self.charging[s]) for s in self.levels}

    def update_battery(self, serial, level, is_charging):
        self.levels[serial] = level
        self.charging[serial] = is_charging
        self.BatteryChanged(serial, level, is_charging)

battery_broadcaster = None

# D-Bus names
NAME = 'io.github.pwr_solaar.solaar_beta.BatteryService'
PATH = '/io/github/pwr_solaar/solaar_beta/Battery'

def setup_battery_broadcaster():
    global battery_broadcaster
    try:
        session_bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(NAME, bus=session_bus)
        battery_broadcaster = BatteryBroadcaster(bus_name, PATH)
        logger.info("Session DBus battery broadcaster started on %s", PATH)
    except Exception as e:
        logger.warning("Failed to start Session DBus battery broadcaster: %s", e)

def broadcast_battery(serial, level, is_charging):
    if battery_broadcaster:
        battery_broadcaster.update_battery(serial, level, is_charging)
