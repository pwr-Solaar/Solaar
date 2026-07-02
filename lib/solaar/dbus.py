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

system_bus: dbus.SystemBus | None = None
session_bus: dbus.SessionBus | None = None

try:
    import dbus

    from dbus.mainloop.glib import DBusGMainLoop  # integration into the main GLib loop

    DBusGMainLoop(set_as_default=True)

    try:
        system_bus = dbus.SystemBus()
    except dbus.exceptions.DBusException as e:
        logger.warning(f"Failed to connect to system dbus: {e}")

    try:
        session_bus = dbus.SessionBus()
    except dbus.exceptions.DBusException as e:
        logger.warning(f"Failed to connect to session dbus: {e}")

except ImportError:
    logger.warning("dbus library not available, dbus setup failed.")
except Exception as e:
    logger.error(f"Unexpected error during D-Bus initialization: {e}")


_suspend_callback = None
_resume_callback = None
_lock_callback = None
_unlock_callback = None


def _suspend_or_resume(suspend):
    if suspend and _suspend_callback:
        _suspend_callback()
    if not suspend and _resume_callback:
        _resume_callback()

def _lock_or_unlock(locked):
    if locked and _lock_callback:
        _lock_callback()
    if not locked and _unlock_callback:
        _unlock_callback()


_LOGIND_PATH = "/org/freedesktop/login1"
_LOGIND_INTERFACE = "org.freedesktop.login1.Manager"
_SCREEN_SAVER_PATH = "/ScreenSaver"
_SCREEN_SAVER_INTERFACE = "org.freedesktop.ScreenSaver"


def watch_suspend_resume(
    on_resume_callback: Callable[[], None] | None = None,
    on_suspend_callback: Callable[[], None] | None = None,
):
    """Register callback for suspend/resume events.
    They are called only if the system DBus is running, and the Login daemon is available."""
    global _resume_callback, _suspend_callback
    _suspend_callback = on_suspend_callback
    _resume_callback = on_resume_callback
    if system_bus is not None and on_resume_callback is not None or on_suspend_callback is not None:
        system_bus.add_signal_receiver(
            _suspend_or_resume,
            "PrepareForSleep",
            dbus_interface=_LOGIND_INTERFACE,
            path=_LOGIND_PATH,
        )
    logger.info("connected to system dbus, watching for suspend/resume events")



def watch_screen_lock_state(
    on_lock_callback: Callable[[], None],
    on_unlock_callback: Callable[[], None],
):
    """Register callbacks for screen lock/unlock events.
    They are called only if the session DBus is running and the Desktop environments sends events on the org.freedesktop.ScreenSaver interface."""
    global _lock_callback, _unlock_callback
    _lock_callback = on_lock_callback
    _unlock_callback = on_unlock_callback
    session_bus.add_signal_receiver(
        _lock_or_unlock,
        "ActiveChanged",
        dbus_interface=_SCREEN_SAVER_INTERFACE,
        path=_SCREEN_SAVER_PATH
    )
    logger.info("connected to session dbus watching for screen lock/unlock events")


_BLUETOOTH_PATH_PREFIX = "/org/bluez/hci0/dev_"
_BLUETOOTH_INTERFACE = "org.freedesktop.DBus.Properties"

_bluetooth_callbacks = {}


def watch_bluez_connect(serial, callback=None):
    if _bluetooth_callbacks.get(serial):
        _bluetooth_callbacks.get(serial).remove()
    path = _BLUETOOTH_PATH_PREFIX + serial.replace(":", "_").upper()
    if system_bus is not None and callback is not None:
        _bluetooth_callbacks[serial] = system_bus.add_signal_receiver(
            callback, "PropertiesChanged", path=path, dbus_interface=_BLUETOOTH_INTERFACE
        )
