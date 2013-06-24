#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
_log = getLogger(__name__)
del getLogger

#
# As suggested here: http://stackoverflow.com/a/13548984
#


_suspend_callback = None
def _suspend():
	if _suspend_callback:
		_log.info("received suspend event from UPower")
		_suspend_callback()


_resume_callback = None
def _resume():
	if _resume_callback:
		_log.info("received resume event from UPower")
		_resume_callback()


def watch(on_resume_callback, on_suspend_callback):
	"""Register callback for suspend/resume events.
	They are called only if the system DBus is running, and the UPower daemon is available."""
	global _resume_callback, _suspend_callback
	_suspend_callback = on_suspend_callback
	_resume_callback = on_resume_callback


try:
	import dbus

	_UPOWER_BUS = 'org.freedesktop.UPower'
	_UPOWER_INTERFACE = 'org.freedesktop.UPower'

	# integration into the main GLib loop
	from dbus.mainloop.glib import DBusGMainLoop
	DBusGMainLoop(set_as_default=True)

	bus = dbus.SystemBus()
	assert bus

	bus.add_signal_receiver(_suspend, signal_name='Sleeping',
					dbus_interface=_UPOWER_INTERFACE, bus_name=_UPOWER_BUS)

	bus.add_signal_receiver(_resume, signal_name='Resuming',
					dbus_interface=_UPOWER_INTERFACE, bus_name=_UPOWER_BUS)

	_log.info("connected to system dbus, watching for suspend/resume events")

except:
	# Either:
	# - the dbus library is not available
	# - the system dbus is not running
	_log.warn("failed to register suspend/resume callbacks")
	pass
