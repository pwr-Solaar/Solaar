#!/usr/bin/env python3

from glob import glob as _glob
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

autostart_path = '/etc/xdg/autostart'

#from solaar import NAME, __version__
__version__ = '1.0.2-rc1'
NAME = 'Solaar'


def _data_files():
	from os.path import dirname as _dirname

	yield 'share/solaar/icons', _glob('share/solaar/icons/solaar*.svg')
	yield 'share/solaar/icons', _glob('share/solaar/icons/light_*.png')
	yield 'share/icons/hicolor/scalable/apps', ['share/solaar/icons/solaar.svg']

	for mo in _glob('share/locale/*/LC_MESSAGES/solaar.mo'):
		yield _dirname(mo), [mo]

	yield 'share/applications', ['share/applications/solaar.desktop']
	yield autostart_path, ['share/autostart/solaar.desktop']
	yield '/etc/udev/rules.d', ['rules.d/42-logitech-unify-permissions.rules']

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
		license='GPLv2',
		url='http://pwr-solaar.github.io/Solaar/',
		classifiers=[
			'Development Status :: 4 - Beta',
			'Environment :: X11 Applications :: GTK',
			'Environment :: Console',
			'Intended Audience :: End Users/Desktop',
			'License :: DFSG approved',
			'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
			'Natural Language :: English',
			'Programming Language :: Python :: 3 :: Only',
			'Operating System :: POSIX :: Linux',
			'Topic :: Utilities',
			],

		platforms=['linux'],

		# sudo apt install python-gi python3-gi \
		#        gir1.2-gtk-3.0 gir1.2-notify-0.7 gir1.2-ayatanaappindicator3-0.1
		# os_requires=['gi.repository.GObject (>= 2.0)', 'gi.repository.Gtk (>= 3.0)'],

		python_requires='>=3.2',
		install_requires=['pyudev (>= 0.13)', ],
		package_dir={'': 'lib'},
		packages=['hidapi', 'logitech_receiver', 'solaar', 'solaar.ui', 'solaar.cli'],
		data_files=list(_data_files()),
		scripts=_glob('bin/*'),
	)
