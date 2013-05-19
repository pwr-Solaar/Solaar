#!/usr/bin/env python

from glob import glob
from distutils.core import setup


setup(name='solaar',
		version='0.8.8.1',
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
		packages=['hidapi', 'logitech', 'logitech.unifying_receiver', 'solaar', 'solaar.ui'],

		data_files=[('share/icons', ['share/solaar/icons/solaar.png']),
					('share/applications', ['share/applications/solaar.desktop']),
					('share/solaar/icons', glob('share/solaar/icons/*.png')),
					],

		scripts=glob('bin/*'),
	)
