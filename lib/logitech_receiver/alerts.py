## Copyright (C) 2012-2013  Daniel Pavel
## Copyright (C) 2014-2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
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

"""Hook for surfacing device-level problems to whatever front end is running.

`logitech_receiver` must not import `solaar.ui`, so the GUI registers a handler
here the same way `solaar.listener` registers its error callback. With no
handler — the CLI, or the tests — alerts fall through to the log.
"""

from __future__ import annotations

import logging

from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)


class AlertReason(Enum):
    # This model's F-row only exists while Solaar maps its G-keys, and
    # /dev/uinput is not writable, so the mapping cannot work.
    GKEYS_NEED_UINPUT = "G-keys need uinput"


_handler: Callable | None = None


def set_handler(handler: Callable | None) -> None:
    """Register the front end's alert handler, called as `handler(reason, device)`."""
    global _handler
    _handler = handler


def notify(reason: AlertReason, device) -> None:
    """Raise an alert about `device`. Always logs; shows UI only if a handler is set."""
    logger.warning("%s: %s", device, reason.value)
    if _handler is None:
        return
    try:
        _handler(reason, device)
    except Exception:
        logger.exception("alert handler failed for %s", reason)
