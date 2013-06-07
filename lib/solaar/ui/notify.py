#
# Optional desktop notifications.
#

from __future__ import absolute_import, division, print_function, unicode_literals


try:
	# this import is allowed to fail, in which case the entire feature is unavailable
	from gi.repository import Notify

	from logging import getLogger, DEBUG as _DEBUG
	_log = getLogger(__name__)
	del getLogger

	from solaar import NAME
	from . import icons as _icons

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
				_log.info("starting desktop notifications")
				try:
					return Notify.init(NAME)
				except:
					_log.exception("initializing desktop notifications")
					available = False
		return available and Notify.is_initted()


	def uninit():
		if available and Notify.is_initted():
			_log.info("stopping desktop notifications")
			_notifications.clear()
			Notify.uninit()


	# def toggle(action):
	# 	if action.get_active():
	# 		init()
	# 	else:
	# 		uninit()
	# 	action.set_sensitive(available)
	# 	return action.get_active()


	def alert(reason, icon=None):
		assert reason

		if available and Notify.is_initted():
			n = _notifications.get(NAME)
			if n is None:
				n = _notifications[NAME] = Notify.Notification()

			# we need to use the filename here because the notifications daemon
			# is an external application that does not know about our icon sets
			icon_file = _icons.icon_file(NAME.lower()) if icon is None \
						else _icons.icon_file(icon)

			n.update(NAME, reason, icon_file)
			n.set_urgency(Notify.Urgency.NORMAL)

			try:
				# if _log.isEnabledFor(_DEBUG):
				# 	_log.debug("showing %s", n)
				n.show()
			except Exception:
				_log.exception("showing %s", n)


	def show(dev, reason=None, icon=None):
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
			icon_file = _icons.device_icon_file(dev.name, dev.kind) if icon is None \
						else _icons.icon_file(icon)

			n.update(summary, message, icon_file)
			urgency = Notify.Urgency.LOW if dev.status else Notify.Urgency.NORMAL
			n.set_urgency(urgency)

			try:
				# if _log.isEnabledFor(_DEBUG):
				# 	_log.debug("showing %s", n)
				n.show()
			except Exception:
				_log.exception("showing %s", n)

except ImportError:
	available = False
	init = lambda: False
	uninit = lambda: None
	# toggle = lambda action: False
	alert = lambda reason: None
	show = lambda dev, reason=None: None
