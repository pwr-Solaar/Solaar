#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from solaar import NAME as _NAME

#
#
#

def _find_locale_path(lc_domain):
	import os.path as _path

	import sys as _sys
	prefix_share = _path.normpath(_path.join(_path.realpath(_sys.path[0]), '..'))
	src_share = _path.normpath(_path.join(_path.realpath(_sys.path[0]), '..', 'share'))
	del _sys

	from glob import glob as _glob

	for location in prefix_share, src_share:
		mo_files = _glob(_path.join(location, 'locale', '*', 'LC_MESSAGES', lc_domain + '.mo'))
		if mo_files:
			return _path.join(location, 'locale')

	# del _path


import locale
locale.setlocale(locale.LC_ALL, '')
language, encoding = locale.getlocale()
del locale

_LOCALE_DOMAIN = _NAME.lower()
path = _find_locale_path(_LOCALE_DOMAIN)

import gettext

gettext.bindtextdomain(_LOCALE_DOMAIN, path)
gettext.textdomain(_LOCALE_DOMAIN)
gettext.install(_LOCALE_DOMAIN)

try:
	unicode
	def _(x):
		return gettext.gettext(x).decode('UTF-8')
except:
	_ = gettext.gettext
