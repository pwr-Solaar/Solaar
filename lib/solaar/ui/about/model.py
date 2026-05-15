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

from datetime import datetime
from typing import List
from typing import Tuple

from solaar import __version__
from solaar.i18n import _


def _get_current_year() -> int:
    return datetime.now().year


class AboutModel:
    def get_version(self) -> str:
        return __version__

    def get_description(self) -> str:
        return _("Manages Logitech receivers,\nkeyboards, mice, and tablets.")

    def get_copyright(self) -> str:
        return f"© 2012-{_get_current_year()} Daniel Pavel and contributors to the Solaar project"

    def get_authors(self) -> List[str]:
        return [
            "Daniel Pavel http://github.com/pwr",
        ]

    def get_translators(self) -> List[str]:
        return [
            "Nikolay Yordanov (Bulgarian)",
            "Rongrong (Chinese Simplified)",
            "Peter Dave Hello (Chinese Taiwan)",
            "gogo (Croatian)",
            "Marián Kyral (Czech)",
            "John Erling Blad (Danish)",
            "Heimen Stoffels (Dutch)",
            "Tomi Leppänen, Niko Savola (Finnish)",
            "Papoteur, David Geiger, Damien Lallement (French)",
            "Daniel Frost (German)",
            "Vangelis Skarmoutsos (Greek)",
            "Ferdina Kusumah (Indonesian)",
            "Michele Olivo, Lorenzo (Italian)",
            "Ryunosuke Toda (Japanese)",
            "John Erling Blad (Norwegian Bokmål, Norwegian Nynorsk)",
            "Adrian Piotrowicz, Matthaiks (Polish)",
            "Américo Monteiro (Portuguese)",
            "Drovetto, Josenivaldo Benito Jr., Vinícius (Brazilian Portuguese)",
            "Daniel Pavel (Romanian)",
            "Dimitriy Ryazantcev, Anton Soroko (Russian)",
            "Renato Kaurić (Serbian)",
            "Jose Riha (Slovak)",
            "Jose Luis Tirado (Spanish)",
            "John Erling Blad, Daniel Zippert, Emelie Snecker, Jonatan Nyberg (Swedish)",
            "Osman Karagöz (Turkish)",
            "Oleksandr Afanasiev (Ukrainian)",
        ]

    def get_credit_sections(self) -> List[Tuple[str, List[str]]]:
        return [
            (_("Additional Programming"), ["Filipe Laíns", "Peter F. Patel-Schneider", "Ken Sanislo"]),
            (_("GUI design"), ["Julien Gascard", "Daniel Pavel"]),
            (
                _("Testing"),
                [
                    "Douglas Wagner",
                    "Julien Gascard",
                    "Peter Wu http://www.lekensteyn.nl/logitech-unifying.html",
                ],
            ),
            (
                _("Logitech documentation"),
                [
                    "Julien Danjou http://julien.danjou.info/blog/2012/logitech-unifying-upower",
                    "Nestor Lopez Casado http://drive.google.com/folderview?id=0BxbRzx7vEV7eWmgwazJ3NUFfQ28",
                ],
            ),
        ]

    def get_website(self):
        return "https://pwr-solaar.github.io/Solaar"
