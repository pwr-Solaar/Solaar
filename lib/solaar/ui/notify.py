#
# Optional desktop notifications.
#

from __future__ import absolute_import, division, print_function, unicode_literals


try:
	# this import is allowed to fail, in which case the entire feature is unavailable
	from gi.repository import Notify
	import logging

	from . import icons as _icons


	_NAMESPACE = 'Solaar'
	# assumed to be working since the import succeeded
	available = True

	# cache references to shown notifications here, so if another status comes
	# while its notification is still visible we don't create another one
	_notifications = {}

	def init():
		"""Init the notifications system."""
		global available
		if available:
			if not Notify.is_initted():
				logging.info("starting desktop notifications")
				try:
					return Notify.init(_NAMESPACE)
				except:
					logging.exception("initializing desktop notifications")
					available = False
		return available and Notify.is_initted()


	def uninit():
		if available and Notify.is_initted():
			logging.info("stopping desktop notifications")
			_notifications.clear()
			Notify.uninit()


	def toggle(action):
		if action.get_active():
			init()
		else:
			uninit()
		action.set_sensitive(available)
		return action.get_active()


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
			n.update(summary, message, _icons.device_icon_file(dev.name, dev.kind))
			urgency = Notify.Urgency.LOW if dev.status else Notify.Urgency.NORMAL
			n.set_urgency(urgency)

			try:
				# logging.debug("showing %s", n)
				n.show()
			except Exception:
				logging.exception("showing %s", n)

except ImportError:
	available = False
	init = lambda: False
	uninit = lambda: None
	toggle = lambda action: False
	show = lambda dev, reason=None: None
