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

import logging

from enum import Enum
from typing import Callable

import gi
import yaml

from logitech_receiver.common import Alert

from solaar.i18n import _
from solaar.ui.config_panel import change_setting
from solaar.ui.config_panel import record_setting
from solaar.ui.window import find_device

from . import common
from . import desktop_notifications
from . import diversion_rules
from . import tray
from . import window

gi.require_version("Gtk", "3.0")
from gi.repository import Gio  # NOQA: E402
from gi.repository import GLib  # NOQA: E402
from gi.repository import Gtk  # NOQA: E402

logger = logging.getLogger(__name__)

assert Gtk.get_major_version() > 2, "Solaar requires Gtk 3 python bindings"


APP_ID = "io.github.pwr_solaar.solaar"


class GtkSignal(Enum):
    ACTIVATE = "activate"
    COMMAND_LINE = "command-line"
    SHUTDOWN = "shutdown"


def _startup(app, startup_hook, use_tray, show_window):
    logger.debug("startup registered=%s, remote=%s", app.get_is_registered(), app.get_is_remote())
    common.start_async()
    desktop_notifications.init()
    if use_tray:
        tray.init(lambda _ignore: window.destroy())
    window.init(show_window, use_tray)
    startup_hook()


def _activate(app):
    logger.debug("activate")
    if app.get_windows():
        window.popup()
    else:
        app.add_window(window._window)


def _command_line(app, command_line):
    args = command_line.get_arguments()
    args = yaml.safe_load("".join(args)) if args else args
    if not args:
        _activate(app)
    elif args[0] == "config":  # config call from remote instance
        logger.info("remote command line %s", args)
        dev = find_device(args[1])
        if dev:
            setting = next((s for s in dev.settings if s.name == args[2]), None)
            if setting:
                change_setting(dev, setting, args[3:])
    return 0


def _shutdown(_app, shutdown_hook):
    logger.debug("shutdown")
    shutdown_hook()
    common.stop_async()
    tray.destroy()
    desktop_notifications.uninit()


def run_loop(
    startup_hook: Callable[[], None],
    shutdown_hook: Callable[[], None],
    use_tray: bool,
    show_window: bool,
):
    assert use_tray or show_window, "need either tray or visible window"

    application = Gtk.Application.new(APP_ID, Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

    application.connect(
        "startup",
        lambda app, startup_hook: _startup(app, startup_hook, use_tray, show_window),
        startup_hook,
    )
    application.connect(GtkSignal.COMMAND_LINE.value, _command_line)
    application.connect(GtkSignal.ACTIVATE.value, _activate)
    application.connect(GtkSignal.SHUTDOWN.value, _shutdown, shutdown_hook)

    application.register()
    if application.get_is_remote():
        print(_("Another Solaar process is already running so just expose its window"))
    application.run()


def _status_changed(device, alert, reason, refresh=False):
    assert device is not None
    logger.debug("status changed: %s (%s) %s", device, alert, reason)
    if alert is None:
        alert = Alert.NONE

    tray.update(device)
    if alert & Alert.ATTENTION:
        tray.attention(reason)

    need_popup = alert & Alert.SHOW_WINDOW
    window.update(device, need_popup, refresh)
    diversion_rules.update_devices()

    if alert & (Alert.NOTIFICATION | Alert.ATTENTION):
        desktop_notifications.show(device, reason)


def status_changed(device, alert=Alert.NONE, reason=None, refresh=False):
    GLib.idle_add(_status_changed, device, alert, reason, refresh)


def setting_changed(device, setting_class, vals):
    record_setting(device, setting_class, vals)
