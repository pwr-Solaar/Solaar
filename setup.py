#!/usr/bin/env python3
import subprocess

from glob import glob as _glob
from os.path import dirname as _dirname

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

NAME = 'Solaar'

with open('lib/solaar/version', 'r') as vfile:
    version = vfile.read().strip()

try:  # get commit from git describe
    commit = subprocess.check_output(['git', 'describe', '--always'], stderr=subprocess.DEVNULL).strip().decode()
    with open('lib/solaar/commit', 'w') as vfile:
        vfile.write(f'{commit}\n')
except Exception:  # get commit from Ubuntu dpkg-parsechangelog
    try:
        commit = subprocess.check_output(['dpkg-parsechangelog', '--show-field', 'Version'],
                                         stderr=subprocess.DEVNULL).strip().decode()
        commit = commit.split('~')
        with open('lib/solaar/commit', 'w') as vfile:
            vfile.write(f'{commit[0]}\n')
    except Exception as e:
        print('Exception using dpkg-parsechangelog', e)


def _data_files():

    yield 'share/icons/hicolor/scalable/apps', _glob('share/solaar/icons/solaar*.svg')
    yield 'share/icons/hicolor/32x32/apps', _glob('share/solaar/icons/solaar-light_*.png')

    for mo in _glob('share/locale/*/LC_MESSAGES/solaar.mo'):
        yield _dirname(mo), [mo]

    yield 'share/applications', ['share/applications/solaar.desktop']
    yield 'lib/udev/rules.d', ['rules.d/42-logitech-unify-permissions.rules']
    yield 'share/metainfo', ['share/solaar/io.github.pwr_solaar.solaar.metainfo.xml']


setup(
    name=NAME.lower(),
    version=version,
    description='Linux device manager for Logitech receivers, keyboards, mice, and tablets.',
    long_description='''
Solaar is a Linux device manager for many Logitech peripherals that connect through
Unifying and other receivers or via USB or Bluetooth.
Solaar is able to pair/unpair devices with receivers and show and modify some of the
modifiable features of devices.
For instructions on installing Solaar see https://pwr-solaar.github.io/Solaar/installation'''.strip(),
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
    python_requires='>=3.7',
    install_requires=[
        'evdev (>= 1.1.2) ; platform_system=="Linux"',
        'pyudev (>= 0.13)',
        'PyYAML (>= 3.12)',
        'python-xlib (>= 0.27)',
        'psutil (>= 5.4.3)',
        'dbus-python ; platform_system=="Linux"',
    ],
    extras_require={
        'report-descriptor': ['hid-parser'],
        'desktop-notifications': ['Notify (>= 0.7)'],
        'git-commit': ['python-git-info'],
        'test': ['pytest'],
    },
    package_dir={'': 'lib'},
    packages=['keysyms', 'hidapi', 'logitech_receiver', 'solaar', 'solaar.ui', 'solaar.cli'],
    data_files=list(_data_files()),
    include_package_data=True,
    scripts=_glob('bin/*'),
)
