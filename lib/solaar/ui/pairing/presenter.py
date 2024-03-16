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

from __future__ import annotations

import logging

from typing import Protocol

from gi.repository import GLib

from solaar.ui.pairing.model import PairingModel

logger = logging.getLogger(__name__)


class PairingViewProtocol(Protocol):
    def init_ui(self, presenter: Presenter, title: str, text: str) -> None:
        ...

    def show_prepare(self, assistant, page):
        ...

    def show_pairing_succeeded(self, receiver, device, glib_timeout_add):
        ...

    def show_pairing_failed(self, receiver, error, title, text):
        ...

    def show_finished(self, receiver):
        ...

    def show_check_lock_state(self, page):
        ...

    def get_current_page(self) -> int:
        ...

    def show_passkey(self, page_title: str, page_text: str):
        ...

    def mainloop(self) -> None:
        ...


class Presenter:
    def __init__(self, model: PairingModel, view: PairingViewProtocol) -> None:
        self.model = model
        self.view = view

    def handle_prepare(self, assistant, page, receiver, show_check_lock_state_cb) -> None:
        index = assistant.get_current_page()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("prepare %s %d %s", assistant, index, page)

        if index == 0:
            self.model.prepare(
                receiver,
                assistant,
                page,
                show_check_lock_state_cb,
                self.handle_check_lock_state,
                self.handle_pairing_failed,
            )
        else:
            assistant.remove_page(0)

    def handle_check_lock_state(self, assistant, receiver, count=2):
        self.model.check_lock_state(
            assistant,
            receiver,
            count,
            pairing_failed_cb=self.handle_pairing_failed,
            pairing_succeeded_cb=self.handle_pairing_succeeded,
            show_passcode_cb=self.handle_passcode,
        )

    def handle_passcode(self, page_title: str, page_text: str):
        self.view.show_passkey(page_title, page_text)

    def handle_pairing_succeeded(self, receiver, device):
        self.view.show_pairing_succeeded(receiver, device, GLib.timeout_add)

    def handle_pairing_failed(self, receiver, error):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s fail: %s", receiver, error)
        title, text = self.model.create_pairing_failed_text(error)
        self.view.show_pairing_failed(title, text)

    def handle_finish(self, receiver, assistant) -> None:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("finish %s", assistant)

        self.view.show_finished()
        self.model.finish()

    def run(self) -> None:
        title = self.model.create_page_title()
        text = self.model.create_page_text()
        receiver = self.model.receiver
        self.view.init_ui(self, receiver, title, text)
        self.view.mainloop()
