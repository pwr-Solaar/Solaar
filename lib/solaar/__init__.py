# -*- python-mode -*-

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

import pkgutil as _pkgutil
import subprocess as _subprocess
import sys as _sys

NAME = 'solaar'

try:
    __version__ = _subprocess.check_output(['git', 'describe', '--always'], cwd=_sys.path[0],
                                           stderr=_subprocess.DEVNULL).strip().decode()
except Exception:
    try:
        __version__ = _pkgutil.get_data('solaar', 'commit').strip().decode()
    except Exception:
        __version__ = _pkgutil.get_data('solaar', 'version').strip().decode()
