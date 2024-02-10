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

import logging

logger = logging.getLogger(__name__)

#
# As suggested here: http://stackoverflow.com/a/13548984
#

_suspend_callback = None


def _suspend():
    if _suspend_callback:
        if logger.isEnabledFor(logging.INFO):
            logger.info('received suspend event')
        _suspend_callback()


_resume_callback = None


def _resume():
    if _resume_callback:
        if logger.isEnabledFor(logging.INFO):
            logger.info('received resume event')
        _resume_callback()


def _suspend_or_resume(suspend):
    _suspend() if suspend else _resume()


def watch(on_resume_callback=None, on_suspend_callback=None):
    """Register callback for suspend/resume events.
    They are called only if the system DBus is running, and the Login daemon is available."""
    global _resume_callback, _suspend_callback
    _suspend_callback = on_suspend_callback
    _resume_callback = on_resume_callback


try:
    import dbus

    _LOGIND_BUS = 'org.freedesktop.login1'
    _LOGIND_INTERFACE = 'org.freedesktop.login1.Manager'

    # integration into the main GLib loop
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()
    assert bus

    bus.add_signal_receiver(_suspend_or_resume, 'PrepareForSleep', dbus_interface=_LOGIND_INTERFACE, bus_name=_LOGIND_BUS)

    if logger.isEnabledFor(logging.INFO):
        logger.info('connected to system dbus, watching for suspend/resume events')

except Exception:
    # Either:
    # - the dbus library is not available
    # - the system dbus is not running
    logger.warning('failed to register suspend/resume callbacks')
    pass
