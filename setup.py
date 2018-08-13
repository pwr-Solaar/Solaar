#!/usr/bin/env python

from glob import glob as _glob
from distutils.core import setup

autostart_path = '/etc/xdg/autostart'

import sys
backup_path_0 = sys.path[0]
sys.path[0] = backup_path_0 + '/lib'
from solaar import NAME, __version__
sys.path[0] = backup_path_0

if 'install' in sys.argv:
	# naively guess where the autostart .desktop file should be installed
	if any(x.startswith('--prefix=') for x in sys.argv) or '--home' in sys.argv:
		autostart_path = 'etc/xdg/autostart'
	elif '--user' in sys.argv:
		from os import environ
		from os import path
		xdg_config_home = environ.get('XDG_CONFIG_HOME', path.expanduser(path.join('~', '.config')))
		autostart_path = path.join(xdg_config_home, 'autostart')
		del environ, path, xdg_config_home

del sys, backup_path_0


def _data_files():
	from os.path import dirname as _dirname

	yield 'share/solaar/icons', _glob('share/solaar/icons/solaar*.svg')
	yield 'share/solaar/icons', _glob('share/solaar/icons/light_*.png')
	yield 'share/icons/hicolor/scalable/apps', ['share/solaar/icons/solaar.svg']

	for mo in _glob('share/locale/*/LC_MESSAGES/solaar.mo'):
		yield _dirname(mo), [mo]

	yield 'share/applications', ['share/applications/solaar.desktop']
	yield autostart_path, ['share/applications/solaar.desktop']

	del _dirname


setup(name=NAME.lower(),
		version=__version__,
		description='Linux devices manager for the Logitech Unifying Receiver.',
		long_description='''
Solaar is a Linux device manager for Logitech's Unifying Receiver peripherals.
It is able to pair/unpair devices to the receiver, and for some devices read
battery status.
'''.strip(),
		author='Daniel Pavel',
		author_email='daniel.pavel@gmail.com',
		license='GPLv2',
		url='http://pwr.github.io/Solaar/',
		classifiers=[
			'Development Status :: 4 - Beta',
			'Environment :: X11 Applications :: GTK',
			'Environment :: Console',
			'Intended Audience :: End Users/Desktop',
			'License :: DFSG approved',
			'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
			'Natural Language :: English',
			'Programming Language :: Python :: 2.7',
			'Programming Language :: Python :: 3.2',
			'Operating System :: POSIX :: Linux',
			'Topic :: Utilities',
			],

		platforms=['linux'],
		requires=['pyudev (>= 0.13)', 'gi.repository.GObject (>= 2.0)', 'gi.repository.Gtk (>= 3.0)'],

		package_dir={'': 'lib'},
		packages=['hidapi', 'logitech_receiver', 'solaar', 'solaar.ui', 'solaar.cli'],
		data_files=list(_data_files()),
		scripts=_glob('bin/*'),
	)
