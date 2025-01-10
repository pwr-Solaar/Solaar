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

import gettext
import locale
import os
import sys

from glob import glob

from solaar import NAME

_LOCALE_DOMAIN = NAME.lower()


def _find_locale_path(locale_domain: str) -> str:
    prefix_share = os.path.normpath(os.path.join(os.path.realpath(sys.path[0]), ".."))
    src_share = os.path.normpath(os.path.join(os.path.realpath(sys.path[0]), "..", "share"))

    for location in prefix_share, src_share:
        mo_files = glob(os.path.join(location, "locale", "*", "LC_MESSAGES", locale_domain + ".mo"))
        if mo_files:
            return os.path.join(location, "locale")
    raise FileNotFoundError(f"Could not find locale path for {locale_domain}")


def set_locale_to_system_default():
    """Sets locale for translations to the system default.

    Set LC_ALL environment variable to enforce a locale setting e.g.
    'de_DE.UTF-8'. Run Solaar with your desired localization, for German
    use:
    'LC_ALL=de_DE.UTF-8 solaar'
    """
    try:
        locale.setlocale(locale.LC_ALL, "")
    except Exception:
        pass

    try:
        path = _find_locale_path(_LOCALE_DOMAIN)
    except FileNotFoundError:
        path = None
    gettext.bindtextdomain(_LOCALE_DOMAIN, path)
    gettext.textdomain(_LOCALE_DOMAIN)
    gettext.install(_LOCALE_DOMAIN)


set_locale_to_system_default()

_ = gettext.gettext
ngettext = gettext.ngettext
