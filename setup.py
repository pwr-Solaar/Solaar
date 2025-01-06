import subprocess
import textwrap

from glob import glob
from os.path import dirname
from pathlib import Path

from setuptools import find_packages
from setuptools import setup

NAME = "Solaar"
version = Path("lib/solaar/version").read_text().strip()

try:  # get commit from git describe
    commit = subprocess.check_output(["git", "describe", "--always"], stderr=subprocess.DEVNULL).strip().decode()
    Path("lib/solaar/commit").write_text(f"{commit}\n")
except Exception:  # get commit from Ubuntu dpkg-parsechangelog
    try:
        commit = (
            subprocess.check_output(["dpkg-parsechangelog", "--show-field", "Version"], stderr=subprocess.DEVNULL)
            .strip()
            .decode()
        )
        commit = commit.split("~")
        Path("lib/solaar/commit").write_text(f"{commit[0]}\n")
    except Exception as e:
        print("Exception using dpkg-parsechangelog", e)


def _data_files():
    yield "share/icons/hicolor/scalable/apps", glob("share/solaar/icons/solaar*.svg")
    yield "share/icons/hicolor/32x32/apps", glob("share/solaar/icons/solaar-light_*.png")

    for mo in glob("share/locale/*/LC_MESSAGES/solaar.mo"):
        yield dirname(mo), [mo]

    yield "share/applications", ["share/applications/solaar.desktop"]
    yield "lib/udev/rules.d", ["rules.d/42-logitech-unify-permissions.rules"]
    yield "share/metainfo", ["share/solaar/io.github.pwr_solaar.solaar.metainfo.xml"]


setup(
    name=NAME.lower(),
    version=version,
    description="Linux device manager for Logitech receivers, keyboards, mice, and tablets.",
    long_description=textwrap.dedent(
        """
        Solaar is a Linux device manager for many Logitech peripherals that connect through
        Unifying and other receivers or via USB or Bluetooth.
        Solaar is able to pair/unpair devices with receivers and show and modify some of the
        modifiable features of devices.
        For instructions on installing Solaar see https://pwr-solaar.github.io/Solaar/installation"""
    ),
    author="Daniel Pavel",
    license="GPLv2",
    url="http://pwr-solaar.github.io/Solaar/",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: GTK",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: DFSG approved",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3 :: Only",
        "Operating System :: POSIX :: Linux",
        "Topic :: Utilities",
    ],
    platforms=["linux"],
    python_requires=">=3.8",
    install_requires=[
        'evdev (>= 1.1.2) ; platform_system=="Linux"',
        "pyudev (>= 0.13)",
        "PyYAML (>= 3.12)",
        "python-xlib (>= 0.27)",
        "psutil (>= 5.4.3)",
        'dbus-python ; platform_system=="Linux"',
        "PyGObject",
        "typing_extensions",
    ],
    extras_require={
        "report-descriptor": ["hid-parser"],
        "desktop-notifications": ["Notify (>= 0.7)"],
        "git-commit": ["python-git-info"],
        "test": ["pytest", "pytest-mock", "pytest-cov"],
        "dev": ["ruff"],
    },
    package_dir={"": "lib"},
    packages=find_packages(where="lib"),
    data_files=list(_data_files()),
    include_package_data=True,
    scripts=glob("bin/*"),
)
