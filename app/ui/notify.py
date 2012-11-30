#
# Optional desktop notifications.
#

import logging


try:
	from gi.repository import Notify

	import ui

	# assumed to be working since the import succeeded
	available = True
	_notifications = {}


	def init(app_title):
		"""Init the notifications system."""
		global available
		if available:
			if not Notify.is_initted():
				logging.info("starting desktop notifications")
				try:
					return Notify.init(app_title)
				except:
					logging.exception("initializing desktop notifications")
					available = False
		return available and Notify.is_initted()


	def uninit():
		if available and Notify.is_initted():
			logging.info("stopping desktop notifications")
			_notifications.clear()
			Notify.uninit()


	def show(dev, reason=None):
		"""Show a notification with title and text."""
		if available and Notify.is_initted():
			summary = dev.name

			# if a notification with same name is already visible, reuse it to avoid spamming
			n = _notifications.get(summary)
			if n is None:
				n = _notifications[summary] = Notify.Notification()

			message = reason or ('unpaired' if dev.status is None else
						(str(dev.status) or ('connected' if dev.status else 'inactive')))

			# we need to use the filename here because the notifications daemon
			# is an external application that does not know about our icon sets
			n.update(summary, message, ui.device_icon_file(dev.name, dev.kind))
			urgency = Notify.Urgency.LOW if dev.status else Notify.Urgency.NORMAL
			n.set_urgency(urgency)

			try:
				# logging.debug("showing %s", n)
				n.show()
			except Exception:
				logging.exception("showing %s", n)

except ImportError:
	available = False
	init = lambda app_title: False
	uninit = lambda: None
	show = lambda dev, reason: None
