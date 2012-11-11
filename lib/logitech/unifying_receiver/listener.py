#
#
#

import threading as _threading

from . import base as _base
from .exceptions import NoReceiver as _NoReceiver
from .common import Packet as _Packet

# for both Python 2 and 3
try:
	from Queue import Queue as _Queue
except ImportError:
	from queue import Queue as _Queue


from logging import getLogger
_log = getLogger('LUR').getChild('listener')
del getLogger


class EventsListener(_threading.Thread):
	"""Listener thread for events from the Unifying Receiver.

	Incoming packets will be passed to the callback function in sequence.
	"""
	def __init__(self, receiver_handle, events_callback):
		super(EventsListener, self).__init__(name=self.__class__.__name__)

		self.daemon = True
		self._active = False

		self._handle = receiver_handle
		self._queued_events = _Queue(32)
		self._events_callback = events_callback

	def run(self):
		self._active = True
		_base.unhandled_hook = self._unhandled_hook
		ihandle = int(self._handle)
		_log.info("started with %s (%d)", repr(self._handle), ihandle)

		while self._active:
			if self._queued_events.empty():
				try:
					# _log.debug("read next event")
					event = _base.read(ihandle)
					# shortcut: we should only be looking at events for proper device numbers
				except _NoReceiver:
					self._active = False
					self._handle = None
					_log.warning("receiver disconnected")
					event = (0xFF, 0xFF, None)
			else:
				# deliver any queued events
				event = self._queued_events.get()

			if event:
				event = _Packet(*event)
				# _log.debug("processing event %s", event)
				try:
					self._events_callback(event)
				except:
					_log.exception("processing event %s", event)

		_base.unhandled_hook = None
		handle, self._handle = self._handle, None
		if handle:
			_base.close(handle)
			_log.info("stopped %s", repr(handle))

	def stop(self):
		"""Tells the listener to stop as soon as possible."""
		if self._active:
			_log.debug("stopping")
			self._active = False
			handle, self._handle = self._handle, None
			if handle:
				_base.close(handle)
				_log.info("stopped %s", repr(handle))

	@property
	def handle(self):
		return self._handle

	def _unhandled_hook(self, reply_code, devnumber, data):
		# only consider unhandled events that were sent from this thread,
		# i.e. triggered during a callback of a previous event
		if _threading.current_thread() == self:
			event = _Packet(reply_code, devnumber, data)
			_log.info("queueing unhandled event %s", event)
			self._queued_events.put(event)

	def __bool__(self):
		return bool(self._active and self._handle)
	__nonzero__ = __bool__
