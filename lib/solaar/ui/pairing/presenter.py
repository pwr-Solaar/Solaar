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

from solaar.ui.pairing.model import PairingModel

logger = logging.getLogger(__name__)


class PairingViewProtocol(Protocol):
    def init_ui(self, presenter, page_title: str, page_text: str) -> None:
        ...

    def show_pairing_succeeded(self, device, handle_check_and_show_encryption_cb):
        ...

    def show_pairing_failed(self, title, text):
        ...

    def show_finished(self):
        ...

    def show_check_lock_state(self, page):
        ...

    def get_current_page(self) -> int:
        ...

    def show_passkey(self, page_title: str, page_text: str):
        ...

    def show_encryption(self, is_link_encrypted):
        ...

    def remove_page(self, page):
        ...

    def mainloop(self) -> None:
        ...

    def is_drawable(self):
        ...


class Presenter:
    def __init__(self, model: PairingModel, view: PairingViewProtocol) -> None:
        self.model = model
        self.view = view

    def handle_prepare(self, assistant, page) -> None:
        page_index = self.view.get_current_page()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("prepare %s %d %s", assistant, page_index, page)
        if page_index == 0:
            self.model.prepare_pairing(
                page, self.view.show_check_lock_state, self.view.show_pairing_failed, self.handle_check_lock_state
            )
        else:
            self.view.remove_page(0)

    def handle_check_lock_state(self, count=2):
        if not self.view.is_drawable():
            return False

        self.model.check_lock_state(
            pairing_failed_cb=self.view.show_pairing_failed,
            pairing_succeeded_cb=self.handle_show_pairing_succeeded,
            show_passcode_cb=self.view.show_passkey,
            count=count,
        )

    def handle_show_pairing_succeeded(self, device):
        encryption_check_and_show_func = self.model.glib_timeout_add(self.handle_encryption_check_and_show)
        self.view.show_pairing_succeeded(device, encryption_check_and_show_func)

    def handle_encryption_check_and_show(self, device, hbox):
        if not self.model.is_device_link_encrypted(device):
            self.view.show_encryption(hbox)

    def handle_close(self, _assistant) -> None:
        self.view.show_finished()
        self.model.finish()

    def run(self) -> None:
        pairing_window_title = self.model.create_page_title()
        pairing_window_text = self.model.create_page_text()
        self.view.init_ui(self, pairing_window_title, pairing_window_text)
        self.view.mainloop()
