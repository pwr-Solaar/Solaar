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
import importlib

# Optional desktop notifications.
import logging

from solaar import NAME
from solaar.i18n import _

from . import icons

logger = logging.getLogger(__name__)


def notifications_available():
    """Checks if notification service is available."""
    notifications_supported = False
    try:
        import gi

        gi.require_version("Notify", "0.7")

        importlib.util.find_spec("gi.repository.GLib")
        importlib.util.find_spec("gi.repository.Notify")

        notifications_supported = True
    except ValueError as e:
        logger.warning(f"Notification service is not available: {e}")
    return notifications_supported


available = notifications_available()

if available:
    from gi.repository import GLib
    from gi.repository import Notify

    # cache references to shown notifications here, so if another status comes
    # while its notification is still visible we don't create another one
    _notifications = {}

    def init():
        """Initialize desktop notifications."""
        global available
        if available:
            if not Notify.is_initted():
                logger.info("starting desktop notifications")
                try:
                    return Notify.init(NAME.lower())
                except Exception:
                    logger.exception("initializing desktop notifications")
                    available = False
        return available and Notify.is_initted()

    def uninit():
        """Stop desktop notifications."""
        if available and Notify.is_initted():
            logger.info("stopping desktop notifications")
            _notifications.clear()
            Notify.uninit()

    def alert(reason, icon=None):
        assert reason

        if available and Notify.is_initted():
            n = _notifications.get(NAME.lower())
            if n is None:
                n = _notifications[NAME.lower()] = Notify.Notification()

            # we need to use the filename here because the notifications daemon
            # is an external application that does not know about our icon sets
            icon_file = icons.icon_file(NAME.lower()) if icon is None else icons.icon_file(icon)

            n.update(NAME.lower(), reason, icon_file)
            n.set_urgency(Notify.Urgency.NORMAL)
            n.set_hint("desktop-entry", GLib.Variant("s", NAME.lower()))

            try:
                n.show()
            except Exception:
                logger.exception("showing %s", n)

    def show(dev, reason=None, icon=None, progress=None):
        """Show a notification with title and text.
        Optionally displays the `progress` integer value
        in [0, 100] as a progress bar."""
        if available and Notify.is_initted():
            summary = dev.name

            # if a notification with same name is already visible, reuse it to avoid spamming
            n = _notifications.get(summary)
            if n is None:
                n = _notifications[summary] = Notify.Notification()

            if reason:
                message = reason
            else:
                message = _("unspecified reason")

            # we need to use the filename here because the notifications daemon
            # is an external application that does not know about our icon sets
            icon_file = icons.device_icon_file(dev.name, dev.kind) if icon is None else icons.icon_file(icon)

            n.update(summary, message, icon_file)
            n.set_urgency(Notify.Urgency.NORMAL)
            n.set_hint("desktop-entry", GLib.Variant("s", NAME.lower()))
            if progress:
                n.set_hint("value", GLib.Variant("i", progress))

            try:
                return n.show()
            except Exception:
                logger.exception(f"showing {n}")

else:

    def init():
        return False

    def uninit():
        return None

    # toggle = lambda action: False
    def alert(reason):
        return None

    def show(dev, reason=None):
        return None
