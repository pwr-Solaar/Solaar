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
"""Generic Human Interface Device API."""

from __future__ import absolute_import, division, print_function, unicode_literals

from hidapi.udev import close  # noqa: F401
from hidapi.udev import enumerate  # noqa: F401
from hidapi.udev import find_paired_node  # noqa: F401
from hidapi.udev import find_paired_node_wpid  # noqa: F401
from hidapi.udev import get_manufacturer  # noqa: F401
from hidapi.udev import get_product  # noqa: F401
from hidapi.udev import get_serial  # noqa: F401
from hidapi.udev import monitor_glib  # noqa: F401
from hidapi.udev import open  # noqa: F401
from hidapi.udev import open_path  # noqa: F401
from hidapi.udev import read  # noqa: F401
from hidapi.udev import write  # noqa: F401

__version__ = '0.9'
