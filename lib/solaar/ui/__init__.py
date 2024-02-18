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

import gi
import yaml as _yaml

from logitech_receiver.status import ALERT
from solaar.i18n import _
from solaar.tasks import TaskRunner as _TaskRunner
from solaar.ui.config_panel import change_setting
from solaar.ui.window import find_device

from . import diversion_rules, notify, tray, window

gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GLib, Gtk  # NOQA: E402

logger = logging.getLogger(__name__)

#
#
#

assert Gtk.get_major_version() > 2, 'Solaar requires Gtk 3 python bindings'

GLib.threads_init()

#
#
#


def _startup(app, startup_hook, use_tray, show_window):
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('startup registered=%s, remote=%s', app.get_is_registered(), app.get_is_remote())

    global _task_runner
    _task_runner = _TaskRunner('AsyncUI')
    _task_runner.start()

    notify.init()
    if use_tray:
        tray.init(lambda _ignore: window.destroy())
    window.init(show_window, use_tray)

    startup_hook()


def _activate(app):
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('activate')
    if app.get_windows():
        window.popup()
    else:
        app.add_window(window._window)


def _command_line(app, command_line):
    args = command_line.get_arguments()
    args = _yaml.safe_load(''.join(args)) if args else args
    if not args:
        _activate(app)
    elif args[0] == 'config':  # config call from remote instance
        if logger.isEnabledFor(logging.INFO):
            logger.info('remote command line %s', args)
        dev = find_device(args[1])
        if dev:
            setting = next((s for s in dev.settings if s.name == args[2]), None)
            if setting:
                change_setting(dev, setting, args[3:])
    return 0


def _shutdown(app, shutdown_hook):
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('shutdown')

    shutdown_hook()

    # stop the async UI processor
    global _task_runner
    _task_runner.stop()
    _task_runner = None

    tray.destroy()
    notify.uninit()


def run_loop(startup_hook, shutdown_hook, use_tray, show_window):
    assert use_tray or show_window, 'need either tray or visible window'
    APP_ID = 'io.github.pwr_solaar.solaar'
    application = Gtk.Application.new(APP_ID, Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

    application.connect('startup', lambda app, startup_hook: _startup(app, startup_hook, use_tray, show_window), startup_hook)
    application.connect('command-line', _command_line)
    application.connect('activate', _activate)
    application.connect('shutdown', _shutdown, shutdown_hook)

    application.register()
    if application.get_is_remote():
        print(_('Another Solaar process is already running so just expose its window'))
    application.run()


#
#
#


def _status_changed(device, alert, reason, refresh=False):
    assert device is not None
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('status changed: %s (%s) %s', device, alert, reason)

    tray.update(device)
    if alert & ALERT.ATTENTION:
        tray.attention(reason)

    need_popup = alert & ALERT.SHOW_WINDOW
    window.update(device, need_popup, refresh)
    diversion_rules.update_devices()

    if alert & (ALERT.NOTIFICATION | ALERT.ATTENTION):
        notify.show(device, reason)


def status_changed(device, alert=ALERT.NONE, reason=None, refresh=False):
    GLib.idle_add(_status_changed, device, alert, reason, refresh)
