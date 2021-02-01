# -*- python-mode -*-
# -*- coding: UTF-8 -*-

## Copyright (C) 2012-2013  Daniel Pavel
## Revisions Copyright (C) Contributors to the Solaar project.
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with this program; if not, write to the Free Software Foundation, Inc.,
## 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from __future__ import absolute_import, division, print_function, unicode_literals

from gi.repository import Gtk
from solaar import NAME, __version__
from solaar.i18n import _

#
#
#

_dialog = None


def _create():
    about = Gtk.AboutDialog()

    about.set_program_name(NAME)
    about.set_version(__version__)
    about.set_comments(_('Shows status of devices connected\nthrough wireless Logitech receivers.'))

    about.set_logo_icon_name(NAME.lower())

    about.set_copyright('© 2012-2021 Daniel Pavel and contributors to the Solaar project')
    about.set_license_type(Gtk.License.GPL_2_0)

    about.set_authors(('Daniel Pavel http://github.com/pwr', ))
    try:
        about.add_credit_section(_('GUI design'), ('Julien Gascard', 'Daniel Pavel'))
        about.add_credit_section(
            _('Testing'), (
                'Douglas Wagner',
                'Julien Gascard',
                'Peter Wu http://www.lekensteyn.nl/logitech-unifying.html',
            )
        )
        about.add_credit_section(
            _('Logitech documentation'), (
                'Julien Danjou http://julien.danjou.info/blog/2012/logitech-unifying-upower',
                'Nestor Lopez Casado http://drive.google.com/folderview?id=0BxbRzx7vEV7eWmgwazJ3NUFfQ28',
            )
        )
    except TypeError:
        # gtk3 < ~3.6.4 has incorrect gi bindings
        import logging
        logging.exception('failed to fully create the about dialog')
    except Exception:
        # the Gtk3 version may be too old, and the function does not exist
        import logging
        logging.exception('failed to fully create the about dialog')

    about.set_translator_credits(
        '\n'.join((
            'gogo (croatian)',
            'Papoteur, David Geiger, Damien Lallement (français)',
            'Michele Olivo (italiano)',
            'Adrian Piotrowicz (polski)',
            'Drovetto, JrBenito (Portuguese-BR)',
            'Daniel Pavel (română)',
            'Daniel Zippert, Emelie Snecker (svensk)',
            'Dimitriy Ryazantcev (Russian)',
        ))
    )

    about.set_website('https://pwr-solaar.github.io/Solaar')
    about.set_website_label(NAME)

    about.connect('response', lambda x, y: x.hide())

    def _hide(dialog, event):
        dialog.hide()
        return True

    about.connect('delete-event', _hide)

    return about


def show_window(trigger=None):
    global _dialog
    if _dialog is None:
        _dialog = _create()
    _dialog.present()
