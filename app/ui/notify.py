#
# Optional desktop notifications.
#

try:
	import notify2 as _notify


	available = True
	_app_title = None
	_images = lambda x: None
	_notifications = {}


	def start(app_title, images=None):
		global _app_title, _images
		_notify.init(app_title)
		_app_title = app_title
		_images = images or (lambda x: None)


	def stop():
		global _app_title
		_app_title = None
		all(n.close() for n in list(_notifications.values()))
		_notify.uninit()
		_notifications.clear()


	def show(status, title, text, icon=None):
		if not _app_title:
			return

		if title in _notifications:
			notification = _notifications[title]
		else:
			_notifications[title] = notification = _notify.Notification(title)

		if text == notification.message:
			# there's no need to show the same notification twice in a row
			return

		path = _images('devices/' + title if icon is None else icon)
		icon = ('error' if status < 0 else 'info') if path is None else path

		notification.update(title, text, icon)
		notification.show()

except ImportError:
	import logging
	logging.exception("ouch")
	logging.warn("python-notify2 not found, desktop notifications are disabled")
	available = False
	def start(app_title): pass
	def stop(): pass
	def show(status, title, text, icon=None): pass
