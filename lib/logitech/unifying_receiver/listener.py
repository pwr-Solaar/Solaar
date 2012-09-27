#
#
#

import logging
import threading
import time

from . import base
from .exceptions import *


_LOG_LEVEL = 6
_l = logging.getLogger('logitech.unifying_receiver.listener')

_EVENT_TIMEOUT = 100
_IDLE_SLEEP = 1000.0 / 1000.0


class EventsListener(threading.Thread):
	def __init__(self, receiver, callback):
		super(EventsListener, self).__init__(name='Unifying_Receiver_Listener_' + str(receiver))

		self.receiver = receiver
		self.callback = callback

		self.task = None
		self.task_processing = threading.Lock()

		self.task_reply = None
		self.task_done = threading.Event()

		self.active = False

	def run(self):
		_l.log(_LOG_LEVEL, "(%d) starting", self.receiver)
		self.active = True
		while self.active:
			# _l.log(_LOG_LEVEL, "(%d) reading next event", self.receiver)
			event = base.read(self.receiver, _EVENT_TIMEOUT)
			if event:
				_l.log(_LOG_LEVEL, "(%d) got event %s", self.receiver, event)
				self.callback.__call__(*event)
			elif self.task is None:
				# _l.log(_LOG_LEVEL, "(%d) idle sleep", self.receiver)
				time.sleep(_IDLE_SLEEP)
			else:
				self.task_reply = self._make_request(*self.task)
				self.task_done.set()

	def stop(self):
		_l.log(_LOG_LEVEL, "(%d) stopping", self.receiver)
		self.active = False
		self.join()

	def request(self, api_function, *args, **kwargs):
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
