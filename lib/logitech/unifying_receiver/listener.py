#
#
#

from threading import Thread as _Thread
# from time import sleep as _sleep

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


_READ_EVENT_TIMEOUT = int(_base.DEFAULT_TIMEOUT / 2)  # ms

def _event_dispatch(listener, callback):
	while listener._active:  # or not listener._events.empty():
		try:
			event = listener._events.get(True, _READ_EVENT_TIMEOUT * 10)
		except:
			continue
		# _log.debug("delivering event %s", event)
		try:
			callback(event)
		except:
			_log.exception("callback for %s", event)


class EventsListener(_Thread):
	"""Listener thread for events from the Unifying Receiver.

	Incoming packets will be passed to the callback function in sequence, by a
	separate thread.
	"""
	def __init__(self, receiver_handle, events_callback):
		super(EventsListener, self).__init__(group='Unifying Receiver', name=self.__class__.__name__)

		self.daemon = True
		self._active = False

		self._handle = receiver_handle

		self._tasks = _Queue(1)
		self._backup_unhandled_hook = _base.unhandled_hook
		_base.unhandled_hook = self.unhandled_hook

		self._events = _Queue(32)
		self._dispatcher = _Thread(group='Unifying Receiver',
									name=self.__class__.__name__ + '-dispatch',
									target=_event_dispatch, args=(self, events_callback))
		self._dispatcher.daemon = True

	def run(self):
		self._active = True
		_log.debug("started")
		_base.request_context = self
		_base.unhandled_hook = self._backup_unhandled_hook
		del self._backup_unhandled_hook

		self._dispatcher.start()

		while self._active:
			try:
				# _log.debug("read next event")
				event = _base.read(self._handle, _READ_EVENT_TIMEOUT)
			except _NoReceiver:
				self._handle = 0
				_log.warn("receiver disconnected")
				self._events.put(_Packet(0xFF, 0xFF, None))
				self._active = False
			else:
				if event is not None:
					matched = False
					task = None if self._tasks.empty() else self._tasks.queue[0]
					if task and task[-1] is None:
						devnumber, data = task[:2]
						if event[1] == devnumber:
							# _log.debug("matching %s to %d, %s", event, devnumber, repr(data))
							if event[0] == 0x11 or (event[0] == 0x10 and devnumber == 0xFF):
								matched = (event[2][:2] == data[:2]) or (event[2][:1] == b'\xFF' and event[2][1:3] == data[:2])
							elif event[0] == 0x10:
								if event[2][:1] == b'\x8F' and event[2][1:3] == data[:2]:
									matched = True

					if matched:
						# _log.debug("request reply %s", event)
						task[-1] = event
						self._tasks.task_done()
					else:
						event = _Packet(*event)
						_log.info("queueing event %s", event)
						self._events.put(event)

		_base.request_context = None
		handle, self._handle = self._handle, 0
		_base.close(handle)
		_log.debug("stopped")

	def stop(self):
		"""Tells the listener to stop as soon as possible."""
		if self._active:
			_log.debug("stopping")
			self._active = False
			# wait for the receiver handle to be closed
			self.join()

	@property
	def handle(self):
		return self._handle

	def write(self, handle, devnumber, data):
		assert handle == self._handle
		# _log.debug("write %02X %s", devnumber, _base._hex(data))
		task = [devnumber, data, None]
		self._tasks.put(task)
		_base.write(self._handle, devnumber, data)
		# _log.debug("task queued %s", task)

	def read(self, handle, timeout=_base.DEFAULT_TIMEOUT):
		assert handle == self._handle
		# _log.debug("read %d", timeout)
		assert not self._tasks.empty()
		self._tasks.join()
		task = self._tasks.get(False)
		# _log.debug("task ready %s", task)
		return task[-1]

	def unhandled_hook(self, reply_code, devnumber, data):
		event = _Packet(reply_code, devnumber, data)
		_log.info("queueing unhandled event %s", event)
		self._events.put(event)

	def __bool__(self):
		return bool(self._active and self._handle)
	__nonzero__ = __bool__
