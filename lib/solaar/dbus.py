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


# Solaar DBus service registration ID
_solaar_service_id = None

# DBus interface XML for window tracking methods
SOLAAR_DBUS_INTERFACE = """
<node>
  <interface name='io.github.pwr_solaar.solaar'>
    <method name='UpdateActiveWindow'>
      <arg type='s' name='wm_class' direction='in'/>
    </method>
    <method name='UpdatePointerOverWindow'>
      <arg type='s' name='wm_class' direction='in'/>
    </method>
  </interface>
</node>
"""


def setup_solaar_dbus_service(connection):
    """Setup DBus service for Solaar to allow external services to notify about window changes.

    This service exposes methods UpdateActiveWindow and UpdatePointerOverWindow that can be
    called by external services (e.g., KDE scripts) to notify Solaar about window changes.

    Args:
        connection: The DBus connection from GTK.Application.get_dbus_connection()
    """
    global _solaar_service_id
    if _solaar_service_id is not None:
        return _solaar_service_id

    if connection is None:
        logger.warning("no DBus connection available, window tracking methods not registered")
        _solaar_service_id = False
        return False

    try:
        from gi.repository import Gio
        from logitech_receiver import diversion

        # Parse the interface XML
        node_info = Gio.DBusNodeInfo.new_for_xml(SOLAAR_DBUS_INTERFACE)
        interface_info = node_info.interfaces[0]

        def handle_method_call(connection, sender, object_path, interface_name, method_name, parameters, invocation):
            """Handle DBus method calls."""
            try:
                if method_name == "UpdateActiveWindow":
                    wm_class = parameters[0]
                    diversion.update_active_window(wm_class)
                    invocation.return_value(None)
                elif method_name == "UpdatePointerOverWindow":
                    wm_class = parameters[0]
                    diversion.update_pointer_over_window(wm_class)
                    invocation.return_value(None)
                else:
                    invocation.return_error_literal(
                        Gio.dbus_error_quark(), Gio.DBusError.UNKNOWN_METHOD, f"Unknown method: {method_name}"
                    )
            except Exception as e:
                logger.error("error handling DBus method call %s: %s", method_name, e)
                invocation.return_error_literal(Gio.dbus_error_quark(), Gio.DBusError.FAILED, f"Internal error: {str(e)}")

        # Register the object on the connection
        _solaar_service_id = connection.register_object(
            "/io/github/pwr_solaar/solaar", interface_info, handle_method_call, None, None
        )

        if _solaar_service_id:
            logger.info("Solaar DBus service methods registered at /io/github/pwr_solaar/solaar")
        else:
            logger.warning("failed to register Solaar DBus service methods")
            _solaar_service_id = False

        return _solaar_service_id
    except Exception as e:
        logger.warning("failed to set up Solaar DBus service: %s", e)
        _solaar_service_id = False
        return False
