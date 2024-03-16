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

from solaar.ui.about.model import AboutModel


class AboutViewProtocol(Protocol):
    def init_ui(self, presenter: Presenter) -> None:
        ...

    def update_credit_sections(self, section_name: str, people: list[str]) -> None:
        ...

    def update_comments(self, comments: str) -> None:
        ...

    def update_authors(self, authors: list[str]) -> None:
        ...

    def update_translator_credits(self, translators: list[str]) -> None:
        ...

    def update_website(self, website):
        ...

    def mainloop(self) -> None:
        ...


class Presenter:
    def __init__(self, model: AboutModel, view: AboutViewProtocol) -> None:
        self.model = model
        self.view = view

    def handle_close(self, event=None) -> None:
        event.hide()

    def update_credit_sections(self) -> None:
        credits_section = self.model.get_credit_sections()
        for section_name, people in credits_section:
            try:
                self.view.update_credit_sections(section_name, people)
            except TypeError:
                # gtk3 < ~3.6.4 has incorrect gi bindings
                logging.exception("failed to fully create the about dialog")
            except Exception:
                # the Gtk3 version may be too old, and the function does not exist
                logging.exception("failed to fully create the about dialog")

    def update_comments(self) -> None:
        comments = self.model.get_comments()
        self.view.update_comments(comments)

    def update_authors(self) -> None:
        authors = self.model.get_authors()
        self.view.update_authors(authors)

    def update_translators(self) -> None:
        translators = self.model.get_translators()
        self.view.update_translator_credits(translators)

    def update_website(self) -> None:
        website = self.model.get_website()
        self.view.update_website(website)

    def run(self) -> None:
        self.view.init_ui(self)
        self.update_credit_sections()
        self.update_comments()
        self.update_authors()
        self.update_translators()
        self.update_website()
        self.view.mainloop()
