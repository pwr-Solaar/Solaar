#
#
#

from logging import getLogger as _Logger
from threading import (Thread, Event, Lock)
from time import sleep as _sleep

from . import base as _base
from . import exceptions as E

# for both Python 2 and 3
try:
	from Queue import Queue
except ImportError:
	from queue import Queue


_LOG_LEVEL = 4
_l = _Logger('lur.listener')


_READ_EVENT_TIMEOUT = int(_base.DEFAULT_TIMEOUT / 5)  # ms
_IDLE_SLEEP = _base.DEFAULT_TIMEOUT / 5  # ms


def _callback_caller(listener, callback):
	# _l.log(_LOG_LEVEL, "%s starting callback caller", listener)
	while listener._active:
		event = listener.events.get()
		_l.log(_LOG_LEVEL, "%s delivering event %s", listener, event)
		try:
			callback.__call__(*event)
		except:
			_l.exception("callback for %s", event)
	# _l.log(_LOG_LEVEL, "%s stopped callback caller", listener)


class EventsListener(Thread):
	"""Listener thread for events from the Unifying Receiver.

	Incoming events (reply_code, devnumber, data) will be passed to the callback
	function in sequence, by a separate thread.

	While this listener is running, you should use the request() method to make
	regular UR API calls, otherwise the expected API replies are most likely to
	be captured by the listener and delivered as events to the callback.
	"""
	def __init__(self, receiver, events_callback):
		super(EventsListener, self).__init__(group='Unifying Receiver', name='Events-%x' % receiver)
		self.daemon = True
		self._active = False

		self.receiver = receiver

		self.task = None
		self.task_processing = Lock()

		self.task_reply = None
		self.task_done = Event()

		self.events = Queue(16)

		self.event_caller = Thread(group='Unifying Receiver', name='Callback-%x' % receiver, target=_callback_caller, args=(self, events_callback))
		self.event_caller.daemon = True

		self.__str_cached = 'Events(%x)' % self.receiver

	def run(self):
		self._active = True
		_l.log(_LOG_LEVEL, "%s started", self)

		self.__str_cached = 'Events(%x:active)' % self.receiver
		self.event_caller.start()

		last_hook = _base.unhandled_hook
		_base.unhandled_hook = self._unhandled

		while self._active:
			try:
				event = _base.read(self.receiver, _READ_EVENT_TIMEOUT)
			except E.NoReceiver:
				_l.warn("%s receiver disconnected", self)
				self._active = False

			if self._active:
				if event:
					# _l.log(_LOG_LEVEL, "%s queueing event %s", self, event)
					self.events.put(event)

				if self.task is None:
					# _l.log(_LOG_LEVEL, "%s idle sleep", self)
					_sleep(_IDLE_SLEEP / 1000.0)
				else:
					self.task_reply = self._make_request(*self.task)
					self.task_done.set()

		_base.close(self.receiver)
		self.__str_cached = 'Events(%x)' % self.receiver

		_base.unhandled_hook = last_hook

	def stop(self):
		"""Tells the listener to stop as soon as possible."""
		_l.log(_LOG_LEVEL, "%s stopping", self)
		self._active = False
		self.join()

	def request(self, api_function, *args, **kwargs):
		"""Make an UR API request through this listener's receiver.

		The api_function must have a receiver handle as a first agument, all
		other passed args and kwargs will follow.
		"""
		# _l.log(_LOG_LEVEL, "%s request '%s.%s' with %s, %s", self, api_function.__module__, api_function.__name__, args, kwargs)

		self.task_processing.acquire()
		self.task_done.clear()
		self.task = (api_function, args, kwargs)

		self.task_done.wait()
		reply = self.task_reply
		self.task = self.task_reply = None
		self.task_processing.release()

		# _l.log(_LOG_LEVEL, "%s request '%s.%s' => %s", self, api_function.__module__, api_function.__name__, repr(reply))
		if isinstance(reply, Exception):
			raise reply
		return reply

	def _make_request(self, api_function, args, kwargs):
		_l.log(_LOG_LEVEL, "%s calling '%s.%s' with %s, %s", self, api_function.__module__, api_function.__name__, args, kwargs)
		try:
			return api_function.__call__(self.receiver, *args, **kwargs)
		except E.NoReceiver as nr:
			self.task_reply = nr
			self._active = False
		except Exception as e:
			self.task_reply = e

	def _unhandled(self, reply_code, devnumber, data):
		event = (reply_code, devnumber, data)
		_l.log(_LOG_LEVEL, "%s queueing unhandled event %s", self, event)
		self.events.put(event)

	def __str__(self):
		return self.__str_cached

	def __nonzero__(self):
		return self._active
