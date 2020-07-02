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

# Translation support for the Logitech receivers library

from __future__ import absolute_import, division, print_function, unicode_literals

import gettext as _gettext

try:
    unicode  # noqa: F821
    _ = lambda x: _gettext.gettext(x).decode('UTF-8')
    ngettext = lambda *x: _gettext.ngettext(*x).decode('UTF-8')
except Exception:
    _ = _gettext.gettext
    ngettext = _gettext.ngettext

# A few common strings, not always accessible as such in the code.

_DUMMY = (
    # approximative battery levels
    _('empty'),
    _('critical'),
    _('low'),
    _('good'),
    _('full'),

    # battery charging statuses
    _('discharging'),
    _('recharging'),
    _('almost full'),
    _('charged'),
    _('slow recharge'),
    _('invalid battery'),
    _('thermal error'),

    # pairing errors
    _('device timeout'),
    _('device not supported'),
    _('too many devices'),
    _('sequence timeout'),

    # firmware kinds
    _('Firmware'),
    _('Bootloader'),
    _('Hardware'),
    _('Other'),
)
