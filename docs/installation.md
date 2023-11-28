---
title: Manual Installation
layout: page
---

# Installing from PyPI

An easy way to install the most recent release version of  Solaar is from the PyPI repository.
First install pip, and then run
`pip install --user solaar`.
If you are using pipx add the `--system-site-packages` flag.

This will not install the Solaar udev rule, which you will need to install manually by copying
`~/.local/share/solaar/udev-rules.d/42-logitech-unify-permissions.rules`
to `/etc/udev/rules.d` as root.

## macOS support

Solaar has limited support for macOS. You can use it to pair devices and configure settings
but the rule system and diversion will not work.

After installing Solaar via pip use homebrew to install the hidapi library:
```
brew install hidapi
```
If you only want to use the CLI that's all that is needed. To use the GUI you need to also
install GTK and its python bindings:
```
brew install gtk+3 pygobject3
```

# Manual installation from GitHub

## Downloading

Clone Solaar from GitHub by `git clone https://github.com/pwr-Solaar/Solaar.git`.

## Requirements for Solaar

If you have previously successfully installed a recent version of Solaar from a repository
you should be able to skip this section.

Solaar needs a reasonably new kernel with kernel modules `hid-logitech-dj`
and `hid-logitech-hidpp` loaded.
Most of Solaar should work fine with any kernel more recent than 5.2,
but newer kernels might be needed for some devices to be correctly recognized and handled.
The `udev` package must be installed and its daemon running.

Solaar requires Python 3.7+ and requires several packages to be installed.
If you are running the system version of Python you should have the
`python3-pyudev`, `python3-psutil`, `python3-xlib`, `python3-evdev`, `python3-typing-extensions`, `dbus-python`,
and `python3-yaml` or `python3-pyyaml` packages installed.

To run the GUI Solaar also requires Gtk3 and its GObject introspection bindings.
If you are running the system version of Python
in Debian/Ubuntu you should have the
`python3-gi` and `gir1.2-gtk-3.0` packages installed.
In Fedora you need `gtk3` and `python3-gobject`.
You may have to install `gcc` and the Python development package (`python3-dev` or `python3-devel`,
depending on your distribution).
Other system packages may be required depending on your distribution, such as `python-gobject-common-devel`.
Although the Solaar CLI does not require Gtk3,
`solaar config` does use Gtk3 capabilities to determine whether the Solaar GUI is running
and thus should tell the Solaar GUI to update its information about settings
so it is a good idea to have Gtk3 available even for the Solaar CLI.

Solaar needs a library to interact with the system tray.
The library that provides this interaction depends on the distribution and window system.
If ayatana appindicator is available then it is best to have this library installed,
e.g., by installing `libayatana-appindicator` or `gir1.2-ayatanaappindicator3-0.1` or similar,
depending on distribution.
Otherwise appindicator can sometimes be used,
e.g., by installing `libappindicator-gtk3` or `gir1.2-appindicator3-0.1` or similar,
depending on distribution.

If desktop notifications bindings are also installed
(`gir1.2-notify-0.7` for Debian/Ubuntu),
you will also see desktop notifications when devices come online and go offline.

If the `hid_parser` Python package is available, Solaar parses HID report descriptors
and can control more HID++ devices that do not use a receiver.
This package may not be available in some distributions but can be installed using pip
via `pip install --user hid-parser`.

If the `gitinfo` Python package is available, Solaar shows better information
about which version of Solaar is running.
This package may not be available in some distributions but can be installed using pip
via `pip install --user python-git-info`.

If you are running a version of Python different from the system version,
you may need to use pip to install projects that provide the above Python packages.

Solaar runs best under X11 with the Xtest extension enabled so that Solaar rules can fake keyboard input using Xtest.
Solaar also uses the X11 library to access the XKB extension,
which requires installation of the X11 development package.
(In Fedora this is `libX11-devel`.  In other distributions it may be `libX11-dev`.)
Solaar will run under Wayland but some parts of Solaar rules will not work.
For more information see [the rules page](https://pwr-solaar.github.io/Solaar/rules).

### Installing Solaar's udev rule

Solaar needs to write to HID devices for receivers and devices.
To be able to do this without running as root requires a udev rule
that gives seated users write access to the HID devices for Logitech receivers and devices.

You can install this rule by copying, as root,
`rules.d/42-logitech-unify-permissions.rules` from Solaar to
`/etc/udev/rules.d`.
You will probably also have to tell udev to reload its rule via
`sudo udevadm control --reload-rules`.

For this rule to set up the correct permissions for your receivers and devices
you will then need to either disconnect your receivers and
any USB-connected or Bluetooth-connected devices and
re-connect them or reboot your computer.

## Running from the download directory

To run Solaar from the download directory, first install the Solaar udev rule if necessary.
Then cd to the solaar directory and run `bin/solaar` for the GUI
or `bin/solaar <command> <arguments>` for the CLI.

Do not run Solaar as root, as you may encounter problems with X11 integration and with the system tray.

## Installing Solaar from the download directory using Pip

Python programs are usually installed using [pip][pip].
The pip instructions for Solaar are in `setup.py`, the standard place to put such instructions.

To install Solaar for yourself only run
`pip install --user '.[report-descriptor,git-commit]'`
from the download directory.
This tells pip to install Solaar into your `~/.local` directory, but does not install Solaar's udev rule.
(See above for installing the udev rule.)
Once the udev rule has been installed you can then run Solaar as `~/.local/bin/solaar`.

Installing Python programs to system directories using pip is generally frowned on both
because this runs arbitrary code as root and because this can override existing python libraries
that other users or even the system depend on. If you want to install Solaar to /usr/local run
`sudo bash -c 'umask 022 ; pip install .'` in the solaar directory.
(The umask is needed so that the created files and directories can be read and executed by everyone.)
Then Solaar can be run as /usr/local/bin/solaar.
You will also have to install the udev rule.

[pip]: https://en.wikipedia.org/wiki/Pip_(package_manager)

## Solaar in other languages

If you want to have Solaar's user messages in some other language you need to run
`tools/po-compile.sh` to create the translation files before running or installing Solaar
and set the LANGUAGE environment variable appropriately when running Solaar.

# Setting up Solaar's icons

Solaar uses a number of custom icons, which have to be installed in a place where GTK can access them.

If Solaar has never been installed, and only run from the download directory then Solaar will not be able to find the icons.
If Solaar has only been installed for a user (e.g., via pip) then Solaar will be able to find the icons,
but they may not show up in the system tray.

One solution is to install a version of Solaar on a system-wide basis.
A more-recent version of Solaar can then be installed for a user or Solaar can be run out of the download directory.
Another solution is to copy the Solaar custom icons from share/solaar/icons to a place they can be found by GTK,
likely /usr/share/icons/hicolor/scalable/apps.

# Running Solaar at Startup

Distributions can cause Solaar can be run automatically at user login by installing a desktop file at
`/etc/xdg/autostart/solaar.desktop`. An example of this file content can be seen in the repository at
[share/autostart/solaar.desktop](https://github.com/pwr-Solaar/Solaar/blob/master/share/autostart/solaar.desktop).

If you install Solaar yourself you may need to create or modify this file or install a startup file under your home directory.
