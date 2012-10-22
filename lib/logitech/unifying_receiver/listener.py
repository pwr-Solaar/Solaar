#
#
#

from logging import getLogger as _Logger
from threading import (Thread, Event, Lock)
# from time import sleep as _sleep

from . import base as _base
from .exceptions import NoReceiver as _NoReceiver
from .common import Packet as _Packet

# for both Python 2 and 3
try:
	from Queue import Queue
except ImportError:
	from queue import Queue


_LOG_LEVEL = 6
_l = _Logger('lur.listener')


_READ_EVENT_TIMEOUT = int(_base.DEFAULT_TIMEOUT / 4)  # ms


def _event_dispatch(listener, callback):
	# _l.log(_LOG_LEVEL, "starting dispatch")
	while listener._active:  # or not listener._events.empty():
		event = listener._events.get()
		_l.log(_LOG_LEVEL, "delivering event %s", event)
		try:
			callback(event)
		except:
			_l.exception("callback for %s", event)
	# _l.log(_LOG_LEVEL, "stopped dispatch")


class EventsListener(Thread):
	"""Listener thread for events from the Unifying Receiver.

	Incoming packets will be passed to the callback function in sequence, by a
	separate thread.

	While this listener is running, you must use the call_api() method to make
	regular UR API calls; otherwise the expected API replies are most likely to
	be captured by the listener and delivered to the callback.
	"""
	def __init__(self, receiver_handle, events_callback):
		super(EventsListener, self).__init__(group='Unifying Receiver', name='%s-%x' % (self.__class__.__name__, receiver_handle))

		self.daemon = True
		self._active = False

		self._handle = receiver_handle

		self._task = None
		self._task_processing = Lock()
		self._task_reply = None
		self._task_done = Event()

		self._events = Queue(32)
		_base.unhandled_hook = self._unhandled

		self._dispatcher = Thread(group='Unifying Receiver',
									name='%s-%x-dispatch' % (self.__class__.__name__, receiver_handle),
									target=_event_dispatch, args=(self, events_callback))
		self._dispatcher.daemon = True

	def run(self):
		self._active = True
		_l.log(_LOG_LEVEL, "started")

		self._dispatcher.start()

		while self._active:
			event = None
			try:
				event = _base.read(self._handle, _READ_EVENT_TIMEOUT)
			except _NoReceiver:
				self._handle = 0
				_l.warn("receiver disconnected")
				self._events.put(_Packet(0xFF, 0xFF, None))
				self._active = False
				break

			if event:
				_l.log(_LOG_LEVEL, "queueing event %s", event)
				self._events.put(_Packet(*event))

			if self._task:
				(api_function, args, kwargs), self._task = self._task, None
				# _l.log(_LOG_LEVEL, "calling '%s.%s' with %s, %s", api_function.__module__, api_function.__name__, args, kwargs)
				try:
					self._task_reply = api_function.__call__(self._handle, *args, **kwargs)
				except _NoReceiver as nr:
					self._handle = 0
					_l.warn("receiver disconnected")
					self._events.put(_Packet(0xFF, 0xFF, None))
					self._task_reply = nr
					self._active = False
					break
				except Exception as e:
					# _l.exception("task %s.%s", api_function.__module__, api_function.__name__)
					self._task_reply = e
				finally:
					self._task_done.set()

		_base.close(self._handle)
		self._handle = 0

	def stop(self):
		"""Tells the listener to stop as soon as possible."""
		if self._active:
			_l.log(_LOG_LEVEL, "stopping")
			self._active = False
			# wait for the receiver handle to be closed
			self.join()

	@property
	def handle(self):
		return self._handle

	def request(self, device, feature_function_index, params=b''):
		return self.call_api(_base.request, device, feature_function_index, params)

	def call_api(self, api_function, *args, **kwargs):
		"""Make an UR API request through this listener's receiver.

		The api_function must have a receiver handle as a first agument, all
		other passed args and kwargs will follow.
		"""
		# _l.log(_LOG_LEVEL, "%s request '%s.%s' with %s, %s", self, api_function.__module__, api_function.__name__, args, kwargs)

		# if not self._active:
		# 	return None

		with self._task_processing:
			self._task_done.clear()
			self._task = (api_function, args, kwargs)
			self._task_done.wait()
			reply, self._task_reply = self._task_reply, None

		# _l.log(_LOG_LEVEL, "%s request '%s.%s' => %s", self, api_function.__module__, api_function.__name__, repr(reply))
		if isinstance(reply, Exception):
			raise reply
		return reply

	def _unhandled(self, reply_code, devnumber, data):
		event = _Packet(reply_code, devnumber, data)
		# _l.log(_LOG_LEVEL, "queueing unhandled event %s", event)
		self._events.put(event)

	def __nonzero__(self):
		return self._active and self._handle
