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

from typing import Protocol
from typing import Union

from gi.repository import Gtk

from solaar import NAME
from solaar import __version__
from solaar.ui.about.presenter import Presenter


class PresenterProtocol(Protocol):
    def handle_close(self, event=None) -> None:
        ...


class AboutView:
    def __init__(self) -> None:
        self.about: Union[Gtk.AboutDialog, None] = None

    def init_ui(self, presenter: Presenter) -> None:
        self.about = Gtk.AboutDialog()
        self.about.set_program_name(NAME)
        self.about.set_version(__version__)
        self.about.set_icon_name(NAME.lower())
        self.about.set_license_type(Gtk.License.GPL_2_0)
        self.about.set_website_label(NAME)

        self.about.connect("response", lambda x, y: presenter.handle_close(x))

    def update_comments(self, comments: str) -> None:
        self.about.set_comments(comments)

    def update_authors(self, authors: list[str]) -> None:
        self.about.set_authors(authors)

    def update_translator_credits(self, translators: list[str]) -> None:
        translator_credits = "\n".join(translators)
        self.about.set_translator_credits(translator_credits)

    def update_website(self, website):
        self.about.set_website(website)

    def mainloop(self) -> None:
        self.about.present()
