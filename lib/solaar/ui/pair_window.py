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

from gi.repository import GLib
from gi.repository import Gtk
from logitech_receiver import hidpp10_constants

from solaar.i18n import _
from solaar.i18n import ngettext

from . import icons

logger = logging.getLogger(__name__)

_PAIRING_TIMEOUT = 30  # seconds
_STATUS_CHECK = 500  # milliseconds


class GtkSignal(Enum):
    CANCEL = "cancel"
    CLOSE = "close"


def create(receiver):
    receiver.reset_pairing()  # clear out any information on previous pairing
    title = _("%(receiver_name)s: pair new device") % {"receiver_name": receiver.name}
    if receiver.receiver_kind == "bolt":
        text = _("Bolt receivers are only compatible with Bolt devices.")
        text += "\n\n"
        text += _("Press a pairing button or key until the pairing light flashes quickly.")
    else:
        if receiver.receiver_kind == "unifying":
            text = _("Unifying receivers are only compatible with Unifying devices.")
        else:
            text = _("Other receivers are only compatible with a few devices.")
        text += "\n\n"
        text += _("For most devices, turn on the device you want to pair.")
        text += _("If the device is already turned on, turn it off and on again.")
        text += "\n"
        text += _("The device must not be paired with a nearby powered-on receiver.")
        text += "\n"
        text += _(
            "For devices with multiple channels, "
            "press, hold, and release the button for the channel you wish to pair"
            "\n"
            "or use the channel switch button to select a channel "
            "and then press, hold, and release the channel switch button."
        )
        text += "\n"
        text += _("The channel indicator light should be blinking rapidly.")
    if receiver.remaining_pairings() and receiver.remaining_pairings() >= 0:
        text += (
            ngettext(
                "\n\nThis receiver has %d pairing remaining.",
                "\n\nThis receiver has %d pairings remaining.",
                receiver.remaining_pairings(),
            )
            % receiver.remaining_pairings()
        )
        text += _("\nCancelling at this point will not use up a pairing.")
    ok = prepare(receiver)
    assistant = _create_assistant(receiver, ok, _finish, title, text)
    if ok:
        GLib.timeout_add(_STATUS_CHECK, check_lock_state, assistant, receiver)
    return assistant


def prepare(receiver):
    if receiver.receiver_kind == "bolt":
        if receiver.discover(timeout=_PAIRING_TIMEOUT):
            return True
        else:
            receiver.pairing.error = "discovery did not start"
            return False
    elif receiver.set_lock(False, timeout=_PAIRING_TIMEOUT):
        return True
    else:
        receiver.pairing.error = "the pairing lock did not open"
        return False


def check_lock_state(assistant, receiver, count=2):
    if not assistant.is_drawable():
        logger.debug("assistant %s destroyed, bailing out", assistant)
        return False
    return _check_lock_state(assistant, receiver, count)


def _check_lock_state(assistant, receiver, count):
    if receiver.pairing.error:
        _pairing_failed(assistant, receiver, receiver.pairing.error)
        return False
    elif receiver.pairing.new_device:
        receiver.remaining_pairings(False)  # Update remaining pairings
        _pairing_succeeded(assistant, receiver, receiver.pairing.new_device)
        return False
    elif not receiver.pairing.lock_open and not receiver.pairing.discovering:
        if count > 0:
            # the actual device notification may arrive later so have a little patience
            GLib.timeout_add(_STATUS_CHECK, check_lock_state, assistant, receiver, count - 1)
        else:
            _pairing_failed(assistant, receiver, "failed to open pairing lock")
        return False
    elif receiver.pairing.lock_open and receiver.pairing.device_passkey:
        _show_passcode(assistant, receiver, receiver.pairing.device_passkey)
        return True
    elif receiver.pairing.discovering and receiver.pairing.device_address and receiver.pairing.device_name:
        add = receiver.pairing.device_address
        ent = 20 if receiver.pairing.device_kind == hidpp10_constants.DEVICE_KIND.keyboard else 10
        if receiver.pair_device(address=add, authentication=receiver.pairing.device_authentication, entropy=ent):
            return True
        else:
            _pairing_failed(assistant, receiver, "failed to open pairing lock")
            return False
    return True


def _pairing_failed(assistant, receiver, error):
    assistant.remove_page(0)  # needed to reset the window size
    logger.debug("%s fail: %s", receiver, error)
    _create_failure_page(assistant, error)


def _pairing_succeeded(assistant, receiver, device):
    assistant.remove_page(0)  # needed to reset the window size
    logger.debug("%s success: %s", receiver, device)
    _create_success_page(assistant, device)


def _finish(assistant, receiver):
    logger.debug("finish %s", assistant)
    assistant.destroy()
    receiver.pairing.new_device = None
    if receiver.pairing.lock_open:
        if receiver.receiver_kind == "bolt":
            receiver.pair_device("cancel")
        else:
            receiver.set_lock()
    if receiver.pairing.discovering:
        receiver.discover(True)
    if not receiver.pairing.lock_open and not receiver.pairing.discovering:
        receiver.pairing.error = None


def _show_passcode(assistant, receiver, passkey):
    logger.debug("%s show passkey: %s", receiver, passkey)
    name = receiver.pairing.device_name
    authentication = receiver.pairing.device_authentication
    intro_text = _("%(receiver_name)s: pair new device") % {"receiver_name": receiver.name}
    page_text = _("Enter passcode on %(name)s.") % {"name": name}
    page_text += "\n"
    if authentication & 0x01:
        page_text += _("Type %(passcode)s and then press the enter key.") % {
            "passcode": receiver.pairing.device_passkey,
        }
    else:
        passcode = ", ".join(
            [_("right") if bit == "1" else _("left") for bit in f"{int(receiver.pairing.device_passkey):010b}"]
        )
        page_text += _("Press %(code)s\nand then press left and right buttons simultaneously.") % {"code": passcode}
    page = _create_page(
        assistant,
        Gtk.AssistantPageType.PROGRESS,
        intro_text,
        "preferences-desktop-peripherals",
        page_text,
    )
    assistant.set_page_complete(page, True)
    assistant.next_page()


def _create_assistant(receiver, ok, finish, title, text):
    assistant = Gtk.Assistant()
    assistant.set_title(title)
    assistant.set_icon_name("list-add")
    assistant.set_size_request(400, 240)
    assistant.set_resizable(False)
    assistant.set_role("pair-device")
    if ok:
        page_intro = _create_page(
            assistant,
            Gtk.AssistantPageType.PROGRESS,
            title,
            "preferences-desktop-peripherals",
            text,
        )
        spinner = Gtk.Spinner()
        spinner.set_visible(True)
        spinner.start()
        page_intro.pack_end(spinner, True, True, 24)
        assistant.set_page_complete(page_intro, True)
    else:
        page_intro = _create_failure_page(assistant, receiver.pairing.error)
    assistant.connect(GtkSignal.CANCEL.value, finish, receiver)
    assistant.connect(GtkSignal.CLOSE.value, finish, receiver)
    return assistant


def _create_success_page(assistant, device):
    def _check_encrypted(device, assistant, hbox):
        if assistant.is_drawable() and device.link_encrypted is False:
            hbox.pack_start(Gtk.Image.new_from_icon_name("security-low", Gtk.IconSize.MENU), False, False, 0)
            hbox.pack_start(Gtk.Label(label=_("The wireless link is not encrypted")), False, False, 0)
            hbox.show_all()
        return False

    page = _create_page(assistant, Gtk.AssistantPageType.SUMMARY)
    header = Gtk.Label(label=_("Found a new device:"))
    page.pack_start(header, False, False, 0)
    device_icon = Gtk.Image()
    icon_name = icons.device_icon_name(device.name, device.kind)
    device_icon.set_from_icon_name(icon_name, icons.LARGE_SIZE)
    page.pack_start(device_icon, True, True, 0)
    device_label = Gtk.Label()
    device_label.set_markup(f"<b>{device.name}</b>")
    page.pack_start(device_label, True, True, 0)
    hbox = Gtk.HBox(homogeneous=False, spacing=8)
    hbox.pack_start(Gtk.Label(label=" "), False, False, 0)
    hbox.set_property("expand", False)
    hbox.set_property("halign", Gtk.Align.CENTER)
    page.pack_start(hbox, False, False, 0)
    GLib.timeout_add(_STATUS_CHECK, _check_encrypted, device, assistant, hbox)  # wait a bit to check link status
    page.show_all()
    assistant.next_page()
    assistant.commit()


def _create_failure_page(assistant, error) -> None:
    header = _("Pairing failed") + ": " + _(str(error)) + "."
    if "timeout" in str(error):
        text = _("Make sure your device is within range, and has a decent battery charge.")
    elif str(error) == "device not supported":
        text = _("A new device was detected, but it is not compatible with this receiver.")
    elif "many" in str(error):
        text = _("More paired devices than receiver can support.")
    else:
        text = _("No further details are available about the error.")
    _create_page(assistant, Gtk.AssistantPageType.SUMMARY, header, "dialog-error", text)
    assistant.next_page()
    assistant.commit()


def _create_page(assistant, kind, header=None, icon_name=None, text=None) -> Gtk.VBox:
    p = Gtk.VBox(homogeneous=False, spacing=8)
    assistant.append_page(p)
    assistant.set_page_type(p, kind)
    if header:
        item = Gtk.HBox(homogeneous=False, spacing=16)
        p.pack_start(item, False, True, 0)
        label = Gtk.Label(label=header)
        label.set_line_wrap(True)
        item.pack_start(label, True, True, 0)
        if icon_name:
            icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
            item.pack_start(icon, False, False, 0)
    if text:
        label = Gtk.Label(label=text)
        label.set_line_wrap(True)
        p.pack_start(label, False, False, 0)
    p.show_all()
    return p
