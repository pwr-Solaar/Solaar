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

# Optional desktop notifications.

from __future__ import absolute_import, division, print_function, unicode_literals

from solaar.i18n import _

#
#
#

try:
    import gi
    gi.require_version('Notify', '0.7')
    # this import is allowed to fail, in which case the entire feature is unavailable
    from gi.repository import Notify, GLib

    # assumed to be working since the import succeeded
    available = True

except (ValueError, ImportError):
    available = False

if available:
    from logging import getLogger, INFO as _INFO
    _log = getLogger(__name__)
    del getLogger

    from solaar import NAME
    from . import icons as _icons

    # cache references to shown notifications here, so if another status comes
    # while its notification is still visible we don't create another one
    _notifications = {}

    def init():
        """Init the notifications system."""
        global available
        if available:
            if not Notify.is_initted():
                if _log.isEnabledFor(_INFO):
                    _log.info('starting desktop notifications')
                try:
                    return Notify.init(NAME)
                except Exception:
                    _log.exception('initializing desktop notifications')
                    available = False
        return available and Notify.is_initted()

    def uninit():
        if available and Notify.is_initted():
            if _log.isEnabledFor(_INFO):
                _log.info('stopping desktop notifications')
            _notifications.clear()
            Notify.uninit()

    # def toggle(action):
    #     if action.get_active():
    #         init()
    #     else:
    #         uninit()
    #     action.set_sensitive(available)
    #     return action.get_active()

    def alert(reason, icon=None):
        assert reason

        if available and Notify.is_initted():
            n = _notifications.get(NAME)
            if n is None:
                n = _notifications[NAME] = Notify.Notification()

            # we need to use the filename here because the notifications daemon
            # is an external application that does not know about our icon sets
            icon_file = _icons.icon_file(NAME.lower()) if icon is None else _icons.icon_file(icon)

            n.update(NAME, reason, icon_file)
            n.set_urgency(Notify.Urgency.NORMAL)
            n.set_hint('desktop-entry', GLib.Variant('s', NAME.lower()))

            try:
                # if _log.isEnabledFor(_DEBUG):
                #     _log.debug("showing %s", n)
                n.show()
            except Exception:
                _log.exception('showing %s', n)

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
            elif dev.status is None:
                message = _('unpaired')
            elif bool(dev.status):
                message = dev.status.to_string() or _('connected')
            else:
                message = _('offline')

            # we need to use the filename here because the notifications daemon
            # is an external application that does not know about our icon sets
            icon_file = _icons.device_icon_file(dev.name, dev.kind) if icon is None else _icons.icon_file(icon)

            n.update(summary, message, icon_file)
            urgency = Notify.Urgency.LOW if dev.status else Notify.Urgency.NORMAL
            n.set_urgency(urgency)
            n.set_hint('desktop-entry', GLib.Variant('s', NAME.lower()))
            if progress:
                n.set_hint('value', GLib.Variant('i', progress))

            try:
                # if _log.isEnabledFor(_DEBUG):
                #     _log.debug("showing %s", n)
                n.show()
            except Exception:
                _log.exception('showing %s', n)

else:
    init = lambda: False
    uninit = lambda: None
    # toggle = lambda action: False
    alert = lambda reason: None
    show = lambda dev, reason=None: None
