## Copyright (C) Solaar Contributors
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

from typing import Optional

from gi.repository import GLib
from logitech_receiver.i18n import ngettext

from solaar.i18n import _

logger = logging.getLogger(__name__)

PAIRING_TIMEOUT_SECONDS = 30
STATUS_CHECK_MILLISECONDS = 500


def _create_page_text(receiver_kind: str, remaining_pairings: Optional[int] = None) -> str:
    if receiver_kind == "unifying":
        page_text = _("Unifying receivers are only compatible with Unifying devices.")
    elif receiver_kind == "bolt":
        page_text = _("Bolt receivers are only compatible with Bolt devices.")
    else:
        page_text = _("Other receivers are only compatible with a few devices.")
    page_text += "\n"
    page_text += _("The device must not be paired with a nearby powered-on receiver.")
    page_text += "\n\n"

    if receiver_kind == "bolt":
        page_text += _("Press a pairing button or key until the pairing light flashes quickly.")
        page_text += "\n"
        page_text += _("You may have to first turn the device off and on again.")
    else:
        page_text += _("Turn on the device you want to pair.")
        page_text += "\n"
        page_text += _("If the device is already turned on, turn it off and on again.")

    if remaining_pairings and remaining_pairings >= 0:
        page_text += (
            ngettext(
                "\n\nThis receiver has %d pairing remaining.",
                "\n\nThis receiver has %d pairings remaining.",
                remaining_pairings,
            )
            % remaining_pairings
        )
        page_text += _("\nCancelling at this point will not use up a pairing.")
    return page_text


class PairingModel:
    def __init__(self, receiver, device_kind_keyboard):
        self.receiver = receiver
        self.hid10_device_kind_keyboard = device_kind_keyboard
        self.address = None
        self.kind = None
        self.authentication = None
        self.name = None
        self.passcode = None

    def get_receiver_name(self) -> str:
        return self.receiver.name

    def get_pairing_failed(self) -> str:
        return self.receiver.pairing.error

    def prepare(
        self, receiver, assistant, page, show_check_lock_state_cb, handle_check_lock_state_cb, handle_pairing_failed_cb
    ):
        if receiver.receiver_kind == "bolt":
            if receiver.discover(timeout=PAIRING_TIMEOUT_SECONDS):
                assert receiver.pairing.new_device is None
                assert receiver.pairing.error is None

                GLib.timeout_add(STATUS_CHECK_MILLISECONDS, handle_check_lock_state_cb, assistant, receiver)
                show_check_lock_state_cb(page)
            else:
                GLib.idle_add(handle_pairing_failed_cb, receiver, "discovery did not start")
        elif receiver.set_lock(False, timeout=PAIRING_TIMEOUT_SECONDS):
            assert receiver.pairing.new_device is None
            assert receiver.pairing.error is None

            GLib.timeout_add(STATUS_CHECK_MILLISECONDS, handle_check_lock_state_cb, assistant, receiver)
            show_check_lock_state_cb(page)
        else:
            GLib.idle_add(handle_pairing_failed_cb, receiver, "the pairing lock did not open")

    def create_pairing_failed_text(self, error) -> tuple[str, str]:
        header = _("Pairing failed") + ": " + _(str(error)) + "."
        if "timeout" in str(error):
            text = _("Make sure your device is within range, and has a decent battery charge.")
        elif str(error) == "device not supported":
            text = _("A new device was detected, but it is not compatible with this receiver.")
        elif "many" in str(error):
            text = _("More paired devices than receiver can support.")
        else:
            text = _("No further details are available about the error.")
        return header, text

    def create_page_text(self):
        receiver_kind = self.receiver.receiver_kind
        remaining_pairings = self.receiver.remaining_pairings()
        return _create_page_text(receiver_kind, remaining_pairings)

    def create_page_title(self) -> str:
        return _("%(receiver_name)s: pair new device") % {"receiver_name": self.receiver.name}

    def create_passkey_text(self) -> tuple[str, str]:
        name = self.receiver.pairing.device_name
        authentication = self.receiver.pairing.device_authentication
        page_title = self.create_page_title()
        device_passkey = self.receiver.pairing.device_passkey

        page_text = _("Enter passcode on %(name)s.") % {"name": name}
        page_text += "\n"
        if authentication & 0x01:
            page_text += _("Type %(passcode)s and then press the enter key.") % {
                "passcode": self.receiver.pairing.device_passkey
            }
        else:
            passcode = ", ".join([_("right") if bit == "1" else _("left") for bit in f"{int(device_passkey):010b}"])
            page_text += _("Press %(code)s\nand then press left and right buttons simultaneously.") % {"code": passcode}
        return page_title, page_text

    def finish(self):
        self.receiver.pairing.new_device = None
        if self.receiver.pairing.lock_open:
            if self.receiver.receiver_kind == "bolt":
                self.receiver.pair_device("cancel")
            else:
                self.receiver.set_lock()
        if self.receiver.pairing.discovering:
            self.receiver.discover(True)
        if not self.receiver.pairing.lock_open and not self.receiver.pairing.discovering:
            self.receiver.pairing.error = None

    def check_lock_state(
        self,
        assistant,
        receiver,
        count=2,
        pairing_failed_cb=None,
        pairing_succeeded_cb=None,
        show_passcode_cb=None,
    ):
        if not assistant.is_drawable():
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("assistant %s destroyed, bailing out", assistant)
            return False

        if receiver.pairing.error:
            pairing_failed_cb(receiver, receiver.pairing.error)
            receiver.pairing.error = None
            return False

        if receiver.pairing.new_device:
            receiver.remaining_pairings(False)  # Update remaining pairings
            device = receiver.pairing.new_device
            receiver.pairing.new_device = None
            pairing_succeeded_cb(receiver, device)
            return False
        elif receiver.pairing.device_address and receiver.pairing.device_name and not self.address:
            self.address = receiver.pairing.device_address
            self.name = receiver.pairing.device_name
            self.kind = receiver.pairing.device_kind
            self.authentication = receiver.pairing.device_authentication
            self.name = receiver.pairing.device_name

            entropy = 10
            if self.kind == self.hid10_device_kind_keyboard:
                entropy = 20
            if receiver.pair_device(
                address=self.address,
                authentication=self.authentication,
                entropy=entropy,
            ):
                return True
            else:
                pairing_failed_cb(receiver, "failed to open pairing lock")
                return False
        elif self.address and receiver.pairing.device_passkey and not self.passcode:
            passcode = receiver.pairing.device_passkey
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s show passkey: %s", receiver, passcode)
            page_title, page_text = self.create_passkey_text()
            show_passcode_cb(page_title, page_text)
            return True

        if not receiver.pairing.lock_open and not receiver.pairing.discovering:
            if count > 0:
                # the actual device notification may arrive later so have a little patience
                GLib.timeout_add(
                    STATUS_CHECK_MILLISECONDS,
                    self.check_lock_state,
                    assistant,
                    receiver,
                    count - 1,
                    pairing_failed_cb,
                    pairing_succeeded_cb,
                    show_passcode_cb,
                )
            else:
                pairing_failed_cb(receiver, "failed to open pairing lock")
            return False

        return True
