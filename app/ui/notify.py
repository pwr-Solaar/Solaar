#
# Optional desktop notifications.
#

import logging


try:
	from gi.repository import Notify

	import ui
	from logitech.devices.constants import STATUS

	# necessary because the notifications daemon does not know about our XDG_DATA_DIRS
	_icons = {}

	def _icon(title):
		if title not in _icons:
			_icons[title] = ui.icon_file(title)

		return _icons.get(title)

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


	def show(dev):
		"""Show a notification with title and text."""
		if available and Notify.is_initted():
			summary = dev.name

			# if a notification with same name is already visible, reuse it to avoid spamming
			n = _notifications.get(summary)
			if n is None:
				n = _notifications[summary] = Notify.Notification()

			n.update(summary, dev.status_text, _icon(summary) or dev.kind)
			urgency = Notify.Urgency.LOW if dev.status > STATUS.CONNECTED else Notify.Urgency.NORMAL
			n.set_urgency(urgency)

			try:
				# logging.debug("showing %s", n)
				n.show()
			except Exception:
				logging.exception("showing %s", n)

except ImportError:
	logging.warn("desktop notifications disabled")
	available = False
	init = lambda app_title: False
	uninit = lambda: None
	show = lambda dev: None
