## Copyright (C) 2024 Solaar contributors
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

"""Implements the desktop notification service."""

import importlib
import logging

logger = logging.getLogger(__name__)


def notifications_available():
    """Checks if notification service is available."""
    notifications_supported = False
    try:
        import gi

        gi.require_version("Notify", "0.7")
        gi.require_version("Gtk", "3.0")

        importlib.util.find_spec("gi.repository.GLib")
        importlib.util.find_spec("gi.repository.Gtk")
        importlib.util.find_spec("gi.repository.Notify")

        notifications_supported = True
    except ValueError as e:
        logger.warning(f"Notification service is not available: {e}")
    return notifications_supported


available = notifications_available()

if available:
    from gi.repository import GLib
    from gi.repository import Gtk
    from gi.repository import Notify

    # cache references to shown notifications here to allow reuse
    _notifications = {}
    _ICON_LISTS = {}

    def init():
        """Initialize desktop notifications."""
        global available
        if available:
            if not Notify.is_initted():
                if logger.isEnabledFor(logging.INFO):
                    logger.info("starting desktop notifications")
                try:
                    return Notify.init("solaar")  # replace with better name later
                except Exception:
                    logger.exception("initializing desktop notifications")
                    available = False
        return available and Notify.is_initted()

    def uninit():
        """Stop desktop notifications."""
        if available and Notify.is_initted():
            if logger.isEnabledFor(logging.INFO):
                logger.info("stopping desktop notifications")
            _notifications.clear()
            Notify.uninit()

    def show(dev, message: str, icon=None):
        """Show a notification with title and text."""
        if available and (Notify.is_initted() or init()):
            summary = dev.name
            n = _notifications.get(summary)  # reuse notification of same name
            if n is None:
                n = _notifications[summary] = Notify.Notification()
            icon_name = device_icon_name(dev.name, dev.kind) if icon is None else icon
            n.update(summary, message, icon_name)
            n.set_urgency(Notify.Urgency.NORMAL)
            n.set_hint("desktop-entry", GLib.Variant("s", "solaar"))  # replace with better name late
            try:
                return n.show()
            except Exception:
                logger.exception(f"showing {n}")

    def device_icon_list(name="_", kind=None):
        icon_list = _ICON_LISTS.get(name)
        if icon_list is None:
            # names of possible icons, in reverse order of likelihood
            # the theme will hopefully pick up the most appropriate
            icon_list = ["preferences-desktop-peripherals"]
            kind = str(kind)
            if kind:
                if kind == "numpad":
                    icon_list += ("input-keyboard", "input-dialpad")
                elif kind == "touchpad":
                    icon_list += ("input-mouse", "input-tablet")
                elif kind == "trackball":
                    icon_list += ("input-mouse",)
                elif kind == "headset":
                    icon_list += ("audio-headphones", "audio-headset")
                icon_list += (f"input-{kind}",)
            _ICON_LISTS[name] = icon_list
        return icon_list

    def device_icon_name(name, kind=None):
        _default_theme = Gtk.IconTheme.get_default()
        icon_list = device_icon_list(name, kind)
        for n in reversed(icon_list):
            if _default_theme.has_icon(n):
                return n

else:

    def init():
        return False

    def uninit():
        return None

    def show(dev, reason=None):
        return None
