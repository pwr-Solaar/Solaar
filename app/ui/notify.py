#
# Optional desktop notifications.
#

try:
	import notify2 as _notify


	available = True
	_notifications = {}


	def start(app_title):
		"""Init the notifications system."""
		_notify.init(app_title)
		return True


	def stop():
		"""Stop the notifications system."""
		for n in list(_notifications.values()):
			try:
				n.close()
			except Exception:
				# DBUS
				pass
		_notifications.clear()
		_notify.uninit()


	def show(status_code, title, text, icon=None):
		"""Show a notification with title and text."""
		if not available:
			return

		if title in _notifications:
			notification = _notifications[title]
		else:
			_notifications[title] = notification = _notify.Notification(title)

		if text == notification.message:
			# there's no need to show the same notification twice in a row
			return

		icon = icon or title
		notification.update(title, text, title)
		try:
			notification.show()
		except Exception:
			# DBUS
			pass


except ImportError:
	import logging
	logging.exception("ouch")
	logging.warn("python-notify2 not found, desktop notifications are disabled")
	available = False
	def start(app_title): pass
	def stop(): pass
	def show(status_code, title, text, icon=None): pass
