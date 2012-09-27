#
#
#

import logging
import threading
from time import sleep

from . import base
from .exceptions import *


_LOG_LEVEL = 6
_l = logging.getLogger('logitech.unifying_receiver.listener')


_READ_EVENT_TIMEOUT = 90  # ms
_IDLE_SLEEP = 900  # ms


class EventsListener(threading.Thread):
	"""Listener thread for events from the Unifying Receiver.

	Incoming events (code, device, data) will be delivered to the callback
	function. The callback is called in the listener thread, so it should return
	as fast as possible.

	While this listener is running, you should use the request() method to make
	regular UR API calls, otherwise the replies will be captured by the listener
	and delivered as events to the callback. As an exception, you can make UR
	API calls in the events callback.
	"""
	def __init__(self, receiver, events_callback):
		super(EventsListener, self).__init__(name='Unifying_Receiver_Listener_' + str(receiver))
		self.daemon = True

		self.receiver = receiver
		self.callback = events_callback

		self.task = None
		self.task_processing = threading.Lock()

		self.task_reply = None
		self.task_done = threading.Event()

	def run(self):
		_l.log(_LOG_LEVEL, "(%d) starting", self.receiver)
		self.active = True
		while self.active:
			try:
				# _l.log(_LOG_LEVEL, "(%d) reading next event", self.receiver)
				event = base.read(self.receiver, _READ_EVENT_TIMEOUT)
			except NoReceiver:
				_l.warn("(%d) receiver disconnected", self.receiver)
				self.active = False
				break

			if self.active:
				if event:
					_l.log(_LOG_LEVEL, "(%d) got event %s", self.receiver, event)
					self.callback.__call__(*event)
				elif self.task is None:
					# _l.log(_LOG_LEVEL, "(%d) idle sleep", self.receiver)
					sleep(_IDLE_SLEEP / 1000.0)
				else:
					self.task_reply = self._make_request(*self.task)
					self.task_done.set()

	def stop(self):
		"""Tells the listener to stop as soon as possible."""
		_l.log(_LOG_LEVEL, "(%d) stopping", self.receiver)
		self.active = False

	def request(self, api_function, *args, **kwargs):
		"""Make an UR API request.

		The api_function will get the receiver handle as a first agument, all
		other args and kwargs will follow.
		"""
		# _l.log(_LOG_LEVEL, "(%d) request '%s' with %s, %s", self.receiver, api_function.__name__, args, kwargs)
		self.task_processing.acquire()
		self.task_done.clear()
		self.task = (api_function, args, kwargs)

		self.task_done.wait()
		reply = self.task_reply
		self.task = self.task_reply = None
		self.task_processing.release()

		# _l.log(_LOG_LEVEL, "(%d) request '%s' => [%s]", self.receiver, api_function.__name__, reply.encode('hex'))
		if isinstance(reply, Exception):
			raise reply
		return reply

	def _make_request(self, api_function, args, kwargs):
		_l.log(_LOG_LEVEL, "(%d) calling '%s' with %s, %s", self.receiver, api_function.__name__, args, kwargs)
		try:
			return api_function.__call__(self.receiver, *args, **kwargs)
		except NoReceiver as nr:
			self.task_reply = nr
			self.active = False
		except Exception as e:
			self.task_reply = e
