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

from typing_extensions import Protocol

from solaar.ui.about.model import AboutModel


class AboutViewProtocol(Protocol):
    def init_ui(self) -> None:
        ...

    def update_version_info(self, version: str) -> None:
        ...

    def update_description(self, comments: str) -> None:
        ...

    def update_copyright(self, copyright_text: str) -> None:
        ...

    def update_authors(self, authors: list[str]) -> None:
        ...

    def update_translators(self, translators: list[str]) -> None:
        ...

    def update_website(self, website):
        ...

    def update_credits(self, credit_sections: list[tuple[str, list[str]]]) -> None:
        ...

    def show(self) -> None:
        ...


class Presenter:
    def __init__(self, model: AboutModel, view: AboutViewProtocol) -> None:
        self.model = model
        self.view = view

    def update_version_info(self) -> None:
        version = self.model.get_version()
        self.view.update_version_info(version)

    def update_credits(self) -> None:
        credit_sections = self.model.get_credit_sections()
        self.view.update_credits(credit_sections)

    def update_description(self) -> None:
        comments = self.model.get_description()
        self.view.update_description(comments)

    def update_copyright(self) -> None:
        copyright_text = self.model.get_copyright()
        self.view.update_copyright(copyright_text)

    def update_authors(self) -> None:
        authors = self.model.get_authors()
        self.view.update_authors(authors)

    def update_translators(self) -> None:
        translators = self.model.get_translators()
        self.view.update_translators(translators)

    def update_website(self) -> None:
        website = self.model.get_website()
        self.view.update_website(website)

    def run(self) -> None:
        self.view.init_ui()
        self.update_version_info()
        self.update_description()
        self.update_website()
        self.update_copyright()
        self.update_authors()
        self.update_credits()
        self.update_translators()
        self.view.show()
