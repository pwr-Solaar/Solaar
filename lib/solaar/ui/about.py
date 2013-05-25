#
#
#
from __future__ import absolute_import, division, print_function, unicode_literals

from gi.repository import Gtk

from solaar import __version__, NAME
from . import icons as _icons


_dialog = None


def _create():
	about = Gtk.AboutDialog()

	icon_file = _icons.icon_file(NAME.lower())
	if icon_file:
		about.set_icon_from_file(icon_file)
	else:
		about.set_icon_name(NAME.lower())

	about.set_program_name(NAME)
	about.set_version(__version__)
	about.set_comments('Shows status of devices connected\nto a Logitech Unifying Receiver.')

	about.set_logo_icon_name(NAME.lower() + '-logo')

	about.set_copyright(b'\xC2\xA9'.decode('utf-8') + ' 2012-2013 Daniel Pavel')
	about.set_license_type(Gtk.License.GPL_2_0)

	about.set_authors(('Daniel Pavel http://github.com/pwr',))
	try:
		about.add_credit_section('Testing', (
						'Douglas Wagner',
						'Julien Gascard',
						'Peter Wu http://www.lekensteyn.nl/logitech-unifying.html',
						))
		about.add_credit_section('Logitech documentation', (
						'Julien Danjou http://julien.danjou.info/blog/2012/logitech-unifying-upower',
						'Nestor Lopez Casado http://drive.google.com/folderview?id=0BxbRzx7vEV7eWmgwazJ3NUFfQ28',
						))
	except TypeError:
		# gtk3 < ~3.6.4 has incorrect gi bindings
		import logging
		logging.exception("failed to fully create the about dialog")
	except:
		# the Gtk3 version may be too old, and the function does not exist
		import logging
		logging.exception("failed to fully create the about dialog")

	about.set_website('http://pwr.github.io/Solaar/')
	about.set_website_label(NAME)

	about.connect('response', lambda x, y: x.hide())

	def _hide(dialog, event):
		dialog.hide()
		return True
	about.connect('delete-event', _hide)

	return about


def show_window(_):
	global _dialog
	if _dialog is None:
		_dialog = _create()
	_dialog.present()
