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

from gi.repository import GLib, Gtk
from logitech_receiver.status import KEYS as _K
from solaar.i18n import _, ngettext

from . import icons as _icons

_log = getLogger(__name__)
del getLogger

#
#
#
_PAIRING_TIMEOUT = 30  # seconds
_STATUS_CHECK = 500  # milliseconds


def _create_page(assistant, kind, header=None, icon_name=None, text=None):
    p = Gtk.VBox(False, 8)
    assistant.append_page(p)
    assistant.set_page_type(p, kind)

    if header:
        item = Gtk.HBox(False, 16)
        p.pack_start(item, False, True, 0)

        label = Gtk.Label(header)
        label.set_alignment(0, 0)
        label.set_line_wrap(True)
        item.pack_start(label, True, True, 0)

        if icon_name:
            icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
            icon.set_alignment(1, 0)
            item.pack_start(icon, False, False, 0)

    if text:
        label = Gtk.Label(text)
        label.set_alignment(0, 0)
        label.set_line_wrap(True)
        p.pack_start(label, False, False, 0)

    p.show_all()
    return p


def _check_lock_state(assistant, receiver, count=2):
    if not assistant.is_drawable():
        if _log.isEnabledFor(_DEBUG):
            _log.debug('assistant %s destroyed, bailing out', assistant)
        return False

    if receiver.status.get(_K.ERROR):
        # receiver.status.new_device = _fake_device(receiver)
        _pairing_failed(assistant, receiver, receiver.status.pop(_K.ERROR))
        return False

    if receiver.status.new_device:
        device, receiver.status.new_device = receiver.status.new_device, None
        _pairing_succeeded(assistant, receiver, device)
        return False

    if not receiver.status.lock_open:
        if count > 0:
            # the actual device notification may arrive after the lock was paired,
            # so have a little patience
            GLib.timeout_add(_STATUS_CHECK, _check_lock_state, assistant, receiver, count - 1)
        else:
            _pairing_failed(assistant, receiver, 'failed to open pairing lock')
        return False

    return True


def _prepare(assistant, page, receiver):
    index = assistant.get_current_page()
    if _log.isEnabledFor(_DEBUG):
        _log.debug('prepare %s %d %s', assistant, index, page)

    if index == 0:
        if receiver.set_lock(False, timeout=_PAIRING_TIMEOUT):
            assert receiver.status.new_device is None
            assert receiver.status.get(_K.ERROR) is None
            spinner = page.get_children()[-1]
            spinner.start()
            GLib.timeout_add(_STATUS_CHECK, _check_lock_state, assistant, receiver)
            assistant.set_page_complete(page, True)
        else:
            GLib.idle_add(_pairing_failed, assistant, receiver, 'the pairing lock did not open')
    else:
        assistant.remove_page(0)


def _finish(assistant, receiver):
    if _log.isEnabledFor(_DEBUG):
        _log.debug('finish %s', assistant)
    assistant.destroy()
    receiver.status.new_device = None
    if receiver.status.lock_open:
        receiver.set_lock()
    else:
        receiver.status[_K.ERROR] = None


def _pairing_failed(assistant, receiver, error):
    if _log.isEnabledFor(_DEBUG):
        _log.debug('%s fail: %s', receiver, error)

    assistant.commit()

    header = _('Pairing failed') + ': ' + _(str(error)) + '.'
    if 'timeout' in str(error):
        text = _('Make sure your device is within range, and has a decent battery charge.')
    elif str(error) == 'device not supported':
        text = _('A new device was detected, but it is not compatible with this receiver.')
    elif 'many' in str(error):
        text = _('More paired devices than receiver can support.')
    else:
        text = _('No further details are available about the error.')
    _create_page(assistant, Gtk.AssistantPageType.SUMMARY, header, 'dialog-error', text)

    assistant.next_page()
    assistant.commit()


def _pairing_succeeded(assistant, receiver, device):
    assert device
    if _log.isEnabledFor(_DEBUG):
        _log.debug('%s success: %s', receiver, device)

    page = _create_page(assistant, Gtk.AssistantPageType.SUMMARY)

    header = Gtk.Label(_('Found a new device:'))
    header.set_alignment(0.5, 0)
    page.pack_start(header, False, False, 0)

    device_icon = Gtk.Image()
    icon_set = _icons.device_icon_set(device.name, device.kind)
    device_icon.set_from_icon_set(icon_set, Gtk.IconSize.LARGE)
    device_icon.set_alignment(0.5, 1)
    page.pack_start(device_icon, True, True, 0)

    device_label = Gtk.Label()
    device_label.set_markup('<b>%s</b>' % device.name)
    device_label.set_alignment(0.5, 0)
    page.pack_start(device_label, True, True, 0)

    hbox = Gtk.HBox(False, 8)
    hbox.pack_start(Gtk.Label(' '), False, False, 0)
    hbox.set_property('expand', False)
    hbox.set_property('halign', Gtk.Align.CENTER)
    page.pack_start(hbox, False, False, 0)

    def _check_encrypted(dev):
        if assistant.is_drawable():
            if device.status.get(_K.LINK_ENCRYPTED) is False:
                hbox.pack_start(Gtk.Image.new_from_icon_name('security-low', Gtk.IconSize.MENU), False, False, 0)
                hbox.pack_start(Gtk.Label(_('The wireless link is not encrypted') + '!'), False, False, 0)
                hbox.show_all()
            else:
                return True

    GLib.timeout_add(_STATUS_CHECK, _check_encrypted, device)

    page.show_all()

    assistant.next_page()
    assistant.commit()


def create(receiver):
    assert receiver is not None
    assert receiver.kind is None

    assistant = Gtk.Assistant()
    assistant.set_title(_('%(receiver_name)s: pair new device') % {'receiver_name': receiver.name})
    assistant.set_icon_name('list-add')

    assistant.set_size_request(400, 240)
    assistant.set_resizable(False)
    assistant.set_role('pair-device')

    page_text = _('If the device is already turned on, turn it off and on again.')
    if receiver.remaining_pairings() and receiver.remaining_pairings() >= 0:
        page_text += ngettext(
            '\n\nThis receiver has %d pairing remaining.', '\n\nThis receiver has %d pairings remaining.',
            receiver.remaining_pairings()
        ) % receiver.remaining_pairings()
        page_text += _('\nCancelling at this point will not use up a pairing.')

    page_intro = _create_page(
        assistant, Gtk.AssistantPageType.PROGRESS, _('Turn on the device you want to pair.'),
        'preferences-desktop-peripherals', page_text
    )
    spinner = Gtk.Spinner()
    spinner.set_visible(True)
    page_intro.pack_end(spinner, True, True, 24)

    assistant.connect('prepare', _prepare, receiver)
    assistant.connect('cancel', _finish, receiver)
    assistant.connect('close', _finish, receiver)

    return assistant
