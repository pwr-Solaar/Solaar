#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals


import logging
_DEBUG = logging.DEBUG
_log = logging.getLogger('solaar.ui')


def _look_for_application_icons():
	import os.path as _path
	import os as _os

	import sys as _sys
	_log.debug("sys.path[0] = %s", _sys.path[0])
	prefix_share = _path.normpath(_path.join(_path.realpath(_sys.path[0]), '..'))
	src_share = _path.normpath(_path.join(_path.realpath(_sys.path[0]), '..', 'share'))
	local_share = _os.environ.get('XDG_DATA_HOME', _path.expanduser('~/.local/share'))
	data_dirs = _os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share')
	del _sys

	share_solaar = [prefix_share] + list(_path.join(x, 'solaar') for x in [src_share, local_share] + data_dirs.split(':'))
	for location in share_solaar:
		if _log.isEnabledFor(_DEBUG):
			_log.debug("looking for icons in %s", location)
		solaar_png = _path.join(location, 'icons', 'solaar-logo.png')
		if _path.exists(solaar_png):
			_os.environ['XDG_DATA_DIRS'] = location + ':' + data_dirs
			_log.info("XDG_DATA_DIRS = %s", _os.environ['XDG_DATA_DIRS'])
			break

	del _os
	# del _path

# look for application-specific icons before initializing Gtk
_look_for_application_icons()


from gi.repository import GLib, Gtk
GLib.threads_init()


def error_dialog(title, text):
	m = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, text)
	m.set_title(title)
	m.run()
	m.destroy()

#
#
#

from . import status_icon
from . import notify, main_window


from . import icons
Gtk.Window.set_default_icon_from_file(icons.icon_file(main_window.NAME.lower()))
# Gtk.Window.set_default_icon_name(main_window.NAME.lower())
