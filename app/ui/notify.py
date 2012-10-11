#
# Optional desktop notifications.
#

import logging


try:
	import notify2 as _notify
	from time import time as timestamp

	available = True  # assumed to be working since the import succeeded
	_active = False  # not yet active
	_app_title = None

	_TIMEOUT = 5 * 60  # after this many seconds assume the notification object is no longer valid
	_notifications = {}


	def init(app_title, active=True):
		"""Init the notifications system."""
		global _app_title
		_app_title = app_title
		return set_active(active)


	def set_active(active=True):
		global available, _active
		if available:
			if active:
				if not _active:
					try:
						_notify.init(_app_title)
						_active = True
					except:
						logging.exception("initializing desktop notifications")
						available = False
			else:
				if _active:
					for n in _notifications.values():
						try:
							n.close()
						except:
							logging.exception("closing notification %s", n)
					try:
						_notify.uninit()
					except:
						logging.exception("stopping desktop notifications")
						available = False
					_active = False
		return _active


	def active():
		return _active


	def show(status_code, title, text='', icon=None):
		"""Show a notification with title and text."""
		if available and _active:
			n = None
			if title in _notifications:
				n = _notifications[title]
				if timestamp() - n.timestamp > _TIMEOUT:
					del _notifications[title]
					n = None

			if n is None:
				n = _notify.Notification(title)
				_notifications[title] = n

			n.update(title, text, icon or title)
			n.timestamp = timestamp()
			try:
				logging.debug("showing notification %s", n)
				n.show()
			except Exception:
				logging.exception("showing notification %s", n)


except ImportError:
	logging.warn("python-notify2 not found, desktop notifications are disabled")
	available = False
	active = False
	def init(app_title, active=True): return False
	def active(): return False
	def set_active(active=True): return False
	def show(status_code, title, text, icon=None): pass
