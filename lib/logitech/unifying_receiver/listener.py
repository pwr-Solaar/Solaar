#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

import threading as _threading
from time import time as _timestamp

# for both Python 2 and 3
try:
	from Queue import Queue as _Queue
except ImportError:
	from queue import Queue as _Queue

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger('LUR').getChild('listener')
del getLogger

from . import base as _base

#
#
#

class ThreadedHandle(object):
	"""A thread-local wrapper with different open handles for each thread.

	Closing a ThreadedHandle will close all handles.
	"""

	__slots__ = ['path', '_local', '_handles']

	def __init__(self, initial_handle, path):
		assert initial_handle
		if type(initial_handle) != int:
			raise TypeError('expected int as initial handle, got %s' % repr(initial_handle))

		assert path
		self.path = path
		self._local = _threading.local()
		self._local.handle = initial_handle
		self._handles = [initial_handle]

	def _open(self):
		handle = _base.open_path(self.path)
		if handle is None:
			_log.error("%s failed to open new handle", repr(self))
		else:
			# _log.debug("%s opened new handle %d", repr(self), handle)
			self._local.handle = handle
			self._handles.append(handle)
			return handle

	def close(self):
		if self._local:
			self._local = None
			handles, self._handles = self._handles, []
			if _log.isEnabledFor(_DEBUG):
				_log.debug("%s closing %s", repr(self), handles)
			for h in handles:
				_base.close(h)

	def __del__(self):
		self.close()

	def __index__(self):
		if self._local:
			try:
				return self._local.handle
			except:
				return self._open()
	__int__ = __index__

	def __str__(self):
		if self._local:
			return str(int(self))
	__unicode__ = __str__

	def __repr__(self):
		return '<ThreadedHandle(%s)>' % self.path

	def __bool__(self):
		return bool(self._local)
	__nonzero__ = __bool__

#
#
#

# How long to wait during a read for the next packet.
# Ideally this should be rather long (10s ?), but the read is blocking
# and this means that when the thread is signalled to stop, it would take
# a while for it to acknowledge it.
_EVENT_READ_TIMEOUT = 500

# After this many read that did not produce a packet, call the tick() method.
_IDLE_READS = 4


class EventsListener(_threading.Thread):
	"""Listener thread for notifications from the Unifying Receiver.

	Incoming packets will be passed to the callback function in sequence.
	"""
	def __init__(self, receiver, notifications_callback):
		super(EventsListener, self).__init__(name=self.__class__.__name__)

		self.daemon = True
		self._active = False

		self.receiver = receiver
		self._queued_notifications = _Queue(32)
		self._notifications_callback = notifications_callback

		self.tick_period = 0

	def run(self):
		self._active = True

		# This is necessary because notification packets might be received
		# during requests made by our callback.
		_base.notifications_hook = self._notifications_hook

		ihandle = int(self.receiver.handle)
		_log.info("started with %s (%d)", self.receiver, ihandle)

		self.has_started()

		last_tick = 0
		idle_reads = 0

		while self._active:
			if self._queued_notifications.empty():
				try:
					# _log.debug("read next notification")
					n = _base.read(ihandle, _EVENT_READ_TIMEOUT)
				except _base.NoReceiver:
					_log.warning("receiver disconnected")
					self.receiver.close()
					break

				if n:
					n = _base.make_notification(*n)
			else:
				# deliver any queued notifications
				n = self._queued_notifications.get()

			if n:
				# if _log.isEnabledFor(_DEBUG):
				# 	_log.debug("processing notification %s", n)
				try:
					self._notifications_callback(n)
				except:
					_log.exception("processing notification %s", n)
			elif self.tick_period:
				idle_reads += 1
				if idle_reads % _IDLE_READS == 0:
					idle_reads = 0
					now = _timestamp()
					if now - last_tick >= self.tick_period:
						last_tick = now
						self.tick(now)

		_base.notifications_hook = None
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

	def tick(self, timestamp):
		"""Called about every tick_period seconds."""
		pass

	def _notifications_hook(self, n):
		# Only consider unhandled notifications that were sent from this thread,
		# i.e. triggered by a callback handling a previous notification.
		if self._active and _threading.current_thread() == self:
			if _log.isEnabledFor(_DEBUG):
				_log.debug("queueing unhandled notification %s", n)
			self._queued_notifications.put(n)

	def __bool__(self):
		return bool(self._active and self.receiver)
	__nonzero__ = __bool__
