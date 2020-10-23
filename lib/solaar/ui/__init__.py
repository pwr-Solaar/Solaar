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

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import DEBUG as _DEBUG
from logging import getLogger

import gi  # isort:skip
gi.require_version('Gtk', '3.0')  # NOQA: E402

from gi.repository import GLib, Gtk  # NOQA: E402 # isort:skip
from logitech_receiver.status import ALERT  # NOQA: E402 # isort:skip
from solaar.i18n import _  # NOQA: E402 # isort:skip

_log = getLogger(__name__)
del getLogger

#
#
#

assert Gtk.get_major_version() > 2, 'Solaar requires Gtk 3 python bindings'

GLib.threads_init()

#
#
#


def _error_dialog(reason, object):
    _log.error('error: %s %s', reason, object)

    if reason == 'permissions':
        title = _('Permissions error')
        text = (
            _('Found a Logitech Receiver (%s), but did not have permission to open it.') % object + '\n\n' +
            _("If you've just installed Solaar, try removing the receiver and plugging it back in.")
        )
    elif reason == 'unpair':
        title = _('Unpairing failed')
        text = (
            _('Failed to unpair %{device} from %{receiver}.').format(device=object.name, receiver=object.receiver.name) +
            '\n\n' + _('The receiver returned an error, with no further details.')
        )
    else:
        raise Exception("ui.error_dialog: don't know how to handle (%s, %s)", reason, object)

    assert title
    assert text

    m = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, text)
    m.set_title(title)
    m.run()
    m.destroy()


def error_dialog(reason, object):
    assert reason is not None
    GLib.idle_add(_error_dialog, reason, object)


#
#
#

_task_runner = None


def ui_async(function, *args, **kwargs):
    if _task_runner:
        _task_runner(function, *args, **kwargs)


#
#
#

from . import notify, tray, window  # isort:skip  # noqa: E402


def _startup(app, startup_hook, use_tray, show_window):
    if _log.isEnabledFor(_DEBUG):
        _log.debug('startup registered=%s, remote=%s', app.get_is_registered(), app.get_is_remote())

    from solaar.tasks import TaskRunner as _TaskRunner
    global _task_runner
    _task_runner = _TaskRunner('AsyncUI')
    _task_runner.start()

    notify.init()
    if use_tray:
        tray.init(lambda _ignore: window.destroy())
    window.init(show_window, use_tray)

    startup_hook()


def _activate(app):
    if _log.isEnabledFor(_DEBUG):
        _log.debug('activate')
    if app.get_windows():
        window.popup()
    else:
        app.add_window(window._window)


def _command_line(app, command_line):
    if _log.isEnabledFor(_DEBUG):
        _log.debug('command_line %s', command_line.get_arguments())

    return 0


def _shutdown(app, shutdown_hook):
    if _log.isEnabledFor(_DEBUG):
        _log.debug('shutdown')

    shutdown_hook()

    # stop the async UI processor
    global _task_runner
    _task_runner.stop()
    _task_runner = None

    tray.destroy()
    notify.uninit()


def run_loop(startup_hook, shutdown_hook, use_tray, show_window, args=None):
    assert use_tray or show_window, 'need either tray or visible window'
    # from gi.repository.Gio import ApplicationFlags as _ApplicationFlags
    APP_ID = 'io.github.pwr.solaar'
    application = Gtk.Application.new(APP_ID, 0)  # _ApplicationFlags.HANDLES_COMMAND_LINE)

    application.connect('startup', lambda app, startup_hook: _startup(app, startup_hook, use_tray, show_window), startup_hook)
    application.connect('command-line', _command_line)
    application.connect('activate', _activate)
    application.connect('shutdown', _shutdown, shutdown_hook)

    application.run(args)


#
#
#


def _status_changed(device, alert, reason, refresh=False):
    assert device is not None
    if _log.isEnabledFor(_DEBUG):
        _log.debug('status changed: %s (%s) %s', device, alert, reason)

    tray.update(device)
    if alert & ALERT.ATTENTION:
        tray.attention(reason)

    need_popup = alert & ALERT.SHOW_WINDOW
    window.update(device, need_popup, refresh)

    if alert & (ALERT.NOTIFICATION | ALERT.ATTENTION):
        notify.show(device, reason)


def status_changed(device, alert=ALERT.NONE, reason=None, refresh=False):
    GLib.idle_add(_status_changed, device, alert, reason, refresh)
