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

"""Exceptions that may be raised by this API."""

from typing import Any


class LogitechReceiverError(Exception):
    """Base class for all exceptions in logitech_receiver package."""

    pass


class ReceiverNotAvailableError(LogitechReceiverError):
    """Raised when a receiver is no longer available.

    Trying to talk through a previously open handle, when the
    receiver is no longer available. Should only happen if the receiver
    is physically disconnected from the machine, or its kernel driver
    module is unloaded.
    """

    def __init__(self, msg: str):
        super().__init__(msg)


class NoSuchDeviceError(LogitechReceiverError):
    """Raised when accessing a device (number) not paired to the receiver."""

    def __init__(self, number: int, receiver: Any, msg: str):
        super().__init__(msg)
        self.number = number
        self.receiver = receiver


class FeatureNotSupportedError(LogitechReceiverError):
    """Raised when trying to request a feature not supported by the device."""

    def __init__(self, msg: str):
        super().__init__(msg)


class FeatureCallError(LogitechReceiverError):
    """Raised if the device replied to a feature call with an error."""

    def __init__(self, msg: str):
        super().__init__(msg)
