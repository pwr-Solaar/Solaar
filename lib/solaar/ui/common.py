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

from enum import Enum
from typing import Tuple

import gi

from logitech_receiver.alerts import AlertReason

from solaar.i18n import _
from solaar.tasks import TaskRunner

gi.require_version("Gtk", "3.0")
from gi.repository import GLib  # NOQA: E402
from gi.repository import Gtk  # NOQA: E402

logger = logging.getLogger(__name__)


class ErrorReason(Enum):
    PERMISSIONS = "Permissions"
    NO_DEVICE = "No device"
    UNPAIR = "Unpair"


def _create_error_text(reason: ErrorReason, object_) -> Tuple[str, str]:
    if reason == ErrorReason.PERMISSIONS:
        title = _("Permissions error")
        text = (
            _("Found a Logitech receiver or device (%s), but did not have permission to open it.") % object_
            + "\n\n"
            + _("If you've just installed Solaar, try disconnecting the receiver or device and then reconnecting it.")
        )
    elif reason == ErrorReason.NO_DEVICE:
        title = _("Cannot connect to device error")
        text = (
            _("Found a Logitech receiver or device at %s, but encountered an error connecting to it.") % object_
            + "\n\n"
            + _("Try disconnecting the device and then reconnecting it or turning it off and then on.")
        )
    elif reason == ErrorReason.UNPAIR:
        title = _("Unpairing failed")
        text = (
            _("Failed to unpair %{device} from %{receiver}.").format(
                device=object_.name,
                receiver=object_.receiver.name,
            )
            + "\n\n"
            + _("The receiver returned an error, with no further details.")
        )
    else:
        raise Exception("ui.error_dialog: don't know how to handle (%s, %s)", reason.name, object_)
    return title, text


def _error_dialog(reason: ErrorReason, object_):
    logger.error("error: %s %s", reason, object_)
    title, text = _create_error_text(reason, object_)

    m = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, text)
    m.set_title(title)
    m.run()
    m.destroy()


def error_dialog(reason: ErrorReason, object_):
    GLib.idle_add(_error_dialog, reason, object_)


_RULES_DOC_URL = "https://pwr-solaar.github.io/Solaar/rules"
_ALERT_DISMISSED = "_gkeys_alert_dismissed"
_alerts_shown = set()  # (reason, device path) pairs already shown this session


def _create_alert_text(reason: AlertReason, device) -> Tuple[str, str]:
    if reason == AlertReason.GKEYS_NEED_UINPUT:
        title = _("Function keys need setup")
        text = (
            _("Your %s has no F-keys in hardware.") % device.name
            + "\n"
            + _("Solaar maps its G-keys to F1-F12, which needs write access to /dev/uinput.")
            + "\n\n"
            + _("Setup: %s") % _RULES_DOC_URL
        )
        return title, text
    raise Exception("ui.alert_dialog: don't know how to handle (%s, %s)", reason.name, device)


def _alert_dialog(reason: AlertReason, device):
    title, text = _create_alert_text(reason, device)

    m = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.WARNING, Gtk.ButtonsType.OK, text)
    m.set_title(title)
    never = Gtk.CheckButton.new_with_label(_("Never show this again"))
    never.set_halign(Gtk.Align.START)
    never.show()
    m.get_content_area().pack_end(never, False, False, 6)
    m.run()
    dismissed = never.get_active()
    m.destroy()

    persister = getattr(device, "persister", None)
    if dismissed and persister is not None:
        persister[_ALERT_DISMISSED] = True


def alert_dialog(reason: AlertReason, device):
    """Warn about `device`, once per session unless the user dismissed it for good."""
    persister = getattr(device, "persister", None)
    if persister is not None and persister.get(_ALERT_DISMISSED):
        return
    key = (reason, getattr(device, "path", None), getattr(device, "number", None))
    if key in _alerts_shown:
        return
    _alerts_shown.add(key)
    GLib.idle_add(_alert_dialog, reason, device)


_task_runner = None


def start_async():
    global _task_runner
    _task_runner = TaskRunner("AsyncUI")
    _task_runner.start()


def stop_async():
    global _task_runner
    _task_runner.stop()
    _task_runner = None


def ui_async(function, *args, **kwargs):
    """Runs a function asynchronously."""
    if _task_runner:
        _task_runner(function, *args, **kwargs)
