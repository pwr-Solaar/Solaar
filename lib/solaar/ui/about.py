#
#
#
from __future__ import absolute_import, division, print_function, unicode_literals

from gi.repository import Gtk

from solaar import __version__, NAME


def show_window(action):
	about = Gtk.AboutDialog()

	about.set_icon_name(NAME.lower())
	about.set_program_name(NAME)
	about.set_logo_icon_name(NAME.lower())
	about.set_version(__version__)
	about.set_comments('Shows status of devices connected\nto a Logitech Unifying Receiver.')

	about.set_copyright(b'\xC2\xA9'.decode('utf-8') + ' 2012-2013 Daniel Pavel')
	about.set_license_type(Gtk.License.GPL_2_0)

	about.set_authors(('Daniel Pavel http://github.com/pwr',))
	try:
		about.add_credit_section('Testing', (
						'Douglas Wagner',
						'Julien Gascard',
						'Peter Wu http://www.lekensteyn.nl/logitech-unifying.html',
						))
		about.add_credit_section('Technical specifications\nprovided by', (
						'Julien Danjou http://julien.danjou.info/blog/2012/logitech-unifying-upower',
						'Nestor Lopez Casado https://drive.google.com/folderview?id=0BxbRzx7vEV7eWmgwazJ3NUFfQ28'
						))
	except TypeError:
		# gtk3 < 3.6 has incorrect gi bindings
		import logging
		logging.exception("failed to fully create the about dialog")
	except:
		# is the Gtk3 version too old?
		import logging
		logging.exception("failed to fully create the about dialog")

	about.set_website('http://pwr.github.io/Solaar/')
	about.set_website_label(NAME)

	about.run()
	about.destroy()
