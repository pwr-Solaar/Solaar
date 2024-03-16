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

from typing import List
from typing import Tuple
from typing import Union

from gi.repository import Gtk

from solaar import NAME


class AboutView:
    def __init__(self) -> None:
        self.about: Union[Gtk.AboutDialog, None] = None

    def init_ui(self) -> None:
        self.about = Gtk.AboutDialog()
        self.about.set_program_name(NAME)
        self.about.set_icon_name(NAME.lower())

        self.about.set_license_type(Gtk.License.GPL_2_0)

        self.about.connect("response", lambda x, y: self.handle_close(x))

    def update_version_info(self, version: str) -> None:
        self.about.set_version(version)

    def update_description(self, comments: str) -> None:
        self.about.set_comments(comments)

    def update_copyright(self, copyright_text: str):
        self.about.set_copyright(copyright_text)

    def update_authors(self, authors: List[str]) -> None:
        self.about.set_authors(authors)

    def update_credits(self, credit_sections: List[Tuple[str, List[str]]]) -> None:
        for section_name, people in credit_sections:
            try:
                self.about.add_credit_section(section_name, people)
            except TypeError:
                # gtk3 < ~3.6.4 has incorrect gi bindings
                logging.exception("failed to fully create the about dialog")
            except Exception:
                # the Gtk3 version may be too old, and the function does not exist
                logging.exception("failed to fully create the about dialog")

    def update_translators(self, translators: List[str]) -> None:
        translator_credits = "\n".join(translators)
        self.about.set_translator_credits(translator_credits)

    def update_website(self, website):
        self.about.set_website_label(NAME)
        self.about.set_website(website)

    def show(self) -> None:
        self.about.present()

    def handle_close(self, event) -> None:
        event.hide()
