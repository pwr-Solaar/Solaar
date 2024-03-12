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

import logging
import queue
import threading

from . import base
from . import exceptions

logger = logging.getLogger(__name__)


class _ThreadedHandle:
    """A thread-local wrapper with different open handles for each thread.
    Closing a ThreadedHandle will close all handles.
    """

    __slots__ = ("path", "_local", "_handles", "_listener")

    def __init__(self, listener, path, handle):
        assert listener is not None
        assert path is not None
        assert handle is not None
        assert isinstance(handle, int)

        self._listener = listener
        self.path = path
        self._local = threading.local()
        # take over the current handle for the thread doing the replacement
        self._local.handle = handle
        self._handles = [handle]

    def _open(self):
        handle = base.open_path(self.path)
        if handle is None:
            logger.error("%r failed to open new handle", self)
        else:
            # if logger.isEnabledFor(logging.DEBUG):
            #     logger.debug("%r opened new handle %d", self, handle)
            self._local.handle = handle
            self._handles.append(handle)
            return handle

    def close(self):
        if self._local:
            self._local = None
            handles, self._handles = self._handles, []
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%r closing %s", self, handles)
            for h in handles:
                base.close(h)

    @property
    def notifications_hook(self):
        if self._listener:
            assert isinstance(self._listener, threading.Thread)
            if threading.current_thread() == self._listener:
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
        return f"<_ThreadedHandle({self.path})>"

    def __bool__(self):
        return bool(self._local)

    __nonzero__ = __bool__


# How long to wait during a read for the next packet, in seconds.
# Ideally this should be rather long (10s ?), but the read is blocking and this means that when the thread
# is signalled to stop, it would take a while for it to acknowledge it.
# Forcibly closing the file handle on another thread does _not_ interrupt the read on Linux systems.
_EVENT_READ_TIMEOUT = 1.0  # in seconds


class EventsListener(threading.Thread):
    """Listener thread for notifications from the Unifying Receiver.
    Incoming packets will be passed to the callback function in sequence.
    """

    def __init__(self, receiver, notifications_callback):
        try:
            path_name = receiver.path.split("/")[2]
        except IndexError:
            path_name = receiver.path
        super().__init__(name=self.__class__.__name__ + ":" + path_name)
        self.daemon = True
        self._active = False
        self.receiver = receiver
        self._queued_notifications = queue.Queue(16)
        self._notifications_callback = notifications_callback

    def run(self):
        self._active = True
        # replace the handle with a threaded one
        self.receiver.handle = _ThreadedHandle(self, self.receiver.path, self.receiver.handle)
        if logger.isEnabledFor(logging.INFO):
            logger.info("started with %s (%d)", self.receiver, int(self.receiver.handle))
        self.has_started()

        if self.receiver.isDevice:  # ping (wired or BT) devices to see if they are really online
            if self.receiver.ping():
                self.receiver.changed(active=True, reason="initialization")

        while self._active:
            if self._queued_notifications.empty():
                try:
                    n = base.read(self.receiver.handle, _EVENT_READ_TIMEOUT)
                except exceptions.NoReceiver:
                    logger.warning("%s disconnected", self.receiver.name)
                    self.receiver.close()
                    break
                if n:
                    n = base.make_notification(*n)
            else:
                n = self._queued_notifications.get()  # deliver any queued notifications
            if n:
                try:
                    self._notifications_callback(n)
                except Exception:
                    logger.exception("processing %s", n)

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

    def _notifications_hook(self, n):
        # Only consider unhandled notifications that were sent from this thread,
        # i.e. triggered by a callback handling a previous notification.
        assert threading.current_thread() == self
        if self._active:  # and threading.current_thread() == self:
            # if logger.isEnabledFor(logging.DEBUG):
            #     logger.debug("queueing unhandled %s", n)
            if not self._queued_notifications.full():
                self._queued_notifications.put(n)

    def __bool__(self):
        return bool(self._active and self.receiver)

    __nonzero__ = __bool__
