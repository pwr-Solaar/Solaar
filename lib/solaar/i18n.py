# -*- python-mode -*-
# -*- coding: UTF-8 -*-

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

from __future__ import absolute_import, division, print_function, unicode_literals

import gettext as _gettext
import locale

from solaar import NAME as _NAME

#
#
#


def _find_locale_path(lc_domain):
    import os.path as _path

    import sys as _sys
    prefix_share = _path.normpath(_path.join(_path.realpath(_sys.path[0]), '..'))
    src_share = _path.normpath(_path.join(_path.realpath(_sys.path[0]), '..', 'share'))
    del _sys

    from glob import glob as _glob

    for location in prefix_share, src_share:
        mo_files = _glob(_path.join(location, 'locale', '*', 'LC_MESSAGES', lc_domain + '.mo'))
        if mo_files:
            return _path.join(location, 'locale')

    # del _path


try:
    locale.setlocale(locale.LC_ALL, '')
except Exception:
    pass

language, encoding = locale.getlocale()
del locale

_LOCALE_DOMAIN = _NAME.lower()
path = _find_locale_path(_LOCALE_DOMAIN)

_gettext.bindtextdomain(_LOCALE_DOMAIN, path)
_gettext.textdomain(_LOCALE_DOMAIN)
_gettext.install(_LOCALE_DOMAIN)

try:
    unicode  # noqa: F821
    _ = lambda x: _gettext.gettext(x).decode('UTF-8')
    ngettext = lambda *x: _gettext.ngettext(*x).decode('UTF-8')
except Exception:
    _ = _gettext.gettext
    ngettext = _gettext.ngettext
