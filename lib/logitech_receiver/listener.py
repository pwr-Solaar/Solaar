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

import threading as _threading

from logging import DEBUG as _DEBUG
from logging import INFO as _INFO
from logging import getLogger

from . import base as _base

# from time import time as _timestamp

# for both Python 2 and 3
try:
    from Queue import Queue as _Queue
except ImportError:
    from queue import Queue as _Queue

_log = getLogger(__name__)
del getLogger

#
#
#


class _ThreadedHandle:
    """A thread-local wrapper with different open handles for each thread.

    Closing a ThreadedHandle will close all handles.
    """

    __slots__ = ('path', '_local', '_handles', '_listener')

    def __init__(self, listener, path, handle):
        assert listener is not None
        assert path is not None
        assert handle is not None
        assert isinstance(handle, int)

        self._listener = listener
        self.path = path
        self._local = _threading.local()
        # take over the current handle for the thread doing the replacement
        self._local.handle = handle
        self._handles = [handle]

    def _open(self):
        handle = _base.open_path(self.path)
        if handle is None:
            _log.error('%r failed to open new handle', self)
        else:
            # if _log.isEnabledFor(_DEBUG):
            #     _log.debug("%r opened new handle %d", self, handle)
            self._local.handle = handle
            self._handles.append(handle)
            return handle

    def close(self):
        if self._local:
            self._local = None
            handles, self._handles = self._handles, []
            if _log.isEnabledFor(_DEBUG):
                _log.debug('%r closing %s', self, handles)
            for h in handles:
                _base.close(h)

    @property
    def notifications_hook(self):
        if self._listener:
            assert isinstance(self._listener, _threading.Thread)
            if _threading.current_thread() == self._listener:
                return self._listener._notifications_hook

    def __del__(self):
        self._listener = None
        self.close()

    def __index__(self):
        if self._local:
            try:
                return self._local.handle
            except Exception:
                return self._open()
        else:
            return -1

    __int__ = __index__

    def __str__(self):
        if self._local:
            return str(int(self))

    def __repr__(self):
        return '<_ThreadedHandle(%s)>' % self.path

    def __bool__(self):
        return bool(self._local)

    __nonzero__ = __bool__


#
#
#

# How long to wait during a read for the next packet, in seconds
# Ideally this should be rather long (10s ?), but the read is blocking
# and this means that when the thread is signalled to stop, it would take
# a while for it to acknowledge it.
# Forcibly closing the file handle on another thread does _not_ interrupt the
# read on Linux systems.
_EVENT_READ_TIMEOUT = 1.  # in seconds

# After this many reads that did not produce a packet, call the tick() method.
# This only happens if tick_period is enabled (>0) for the Listener instance.
# _IDLE_READS = 1 + int(5 // _EVENT_READ_TIMEOUT)  # wait at least 5 seconds between ticks


class EventsListener(_threading.Thread):
    """Listener thread for notifications from the Unifying Receiver.

    Incoming packets will be passed to the callback function in sequence.
    """

    def __init__(self, receiver, notifications_callback):
        super().__init__(name=self.__class__.__name__ + ':' + receiver.path.split('/')[2])
        self.daemon = True
        self._active = False
        self.receiver = receiver
        self._queued_notifications = _Queue(16)
        self._notifications_callback = notifications_callback

    def run(self):
        self._active = True
        # replace the handle with a threaded one
        self.receiver.handle = _ThreadedHandle(self, self.receiver.path, self.receiver.handle)
        if _log.isEnabledFor(_INFO):
            _log.info('started with %s (%d)', self.receiver, int(self.receiver.handle))
        self.has_started()

        if self.receiver.isDevice:  # ping (wired or BT) devices to see if they are really online
            if self.receiver.ping():
                self.receiver.status.changed(True, reason='initialization')

        while self._active:
            if self._queued_notifications.empty():
                try:
                    n = _base.read(self.receiver.handle, _EVENT_READ_TIMEOUT)
                except _base.NoReceiver:
                    _log.warning('%s disconnected', self.receiver.name)
                    self.receiver.close()
                    break
                if n:
                    n = _base.make_notification(*n)
            else:
                n = self._queued_notifications.get()  # deliver any queued notifications
            if n:
                try:
                    self._notifications_callback(n)
                except Exception:
                    _log.exception('processing %s', n)

        del self._queued_notifications
        self.has_stopped()

    def stop(self):
        """Tells the listener to stop as soon as possible."""
        self._active = False

    def has_started(self):
        """Called right after the thread has started, and before it starts
        reading notification packets."""
        pass

    def has_stopped(self):
        """Called right before the thread stops."""
        pass

    # def tick(self, timestamp):
    #     """Called about every tick_period seconds."""
    #     pass

    def _notifications_hook(self, n):
        # Only consider unhandled notifications that were sent from this thread,
        # i.e. triggered by a callback handling a previous notification.
        assert _threading.current_thread() == self
        if self._active:  # and _threading.current_thread() == self:
            # if _log.isEnabledFor(_DEBUG):
            #     _log.debug("queueing unhandled %s", n)
            if not self._queued_notifications.full():
                self._queued_notifications.put(n)

    def __bool__(self):
        return bool(self._active and self.receiver)

    __nonzero__ = __bool__
