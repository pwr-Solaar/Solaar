---
title: Manual Installation
layout: page
---

# Manual installation

## Downloading

Clone Solaar from GitHub by `git clone https://github.com/pwr-Solaar/Solaar.git`.

## Requirements for Solaar

Installing Solaar from a repository should have set up all these requirements
so in this situation you should be able to skip this section.

Solaar needs a reasonably new kernel with kernel modules `hid-logitech-dj`
and `hid-logitech-hidpp` loaded.
Most of Solaar should work fine with any kernel more recent than 5.2,
but newer kernels might be needed for some devices to be correctly recognized and handled.
The `udev` package must be installed and its daemon running.

Solaar requires Python 3.7+ and requires several packages to be installed.
If you are running the system version of Python you should have the
`python3-pyudev`, `python3-psutil`, `python3-xlib`, `python3-evdev`,
`python3-typing-extensions`,
and `python3-yaml` or `python3-pyyaml` packages installed.

To run the GUI Solaar also requires Gtk3 and its GObject introspection bindings.
If you are running the system version of Python
the Debian/Ubuntu packages you should have
`python3-gi` and `gir1.2-gtk-3.0` installed.
in Fedora you need `gtk3` and `python3-gobject`.
You may have to install `gcc` and the Python development package (`python3-dev` or `python3-devel`,
depending on your distribution).
Although the Solaar CLI does not require Gtk3,
`solaar config` does use Gtk3 capabilities to determine whether the Solaar GUI is running
and thus should tell the Solaar GUI to update its information about settings
so it is a good idea to have Gtk3 available even for the Solaar CLI.

If the `hid_parser` Python package is available, Solaar parses HID report descriptors
and can control more HID++ devices that do not use a receiver.
This package may not be available in some distributions but can be installed using pip
via `pip install --user hid-parser`.

If you are running a version of Python different from the system version,
you may need to use pip to install projects that provide the above Python packages.

Solaar runs best under X11 with the Xtest extension enabled so that Solaar rules can fake keyboard input using Xtest.
Solaar also uses the X11 library to access the XKB extension,
which requires installation of the X11 development package.
(In Fedora this is `libX11-devel`.  In other distributions it may be `libX11-dev`.)
Solaar will run under Wayland but some parts of Solaar rules will not work.
For more information see [the rules page](https://pwr-solaar.github.io/Solaar/rules).

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
you will also see desktop notifications when devices come online/go offline.

### Installing Solaar's udev rule

Solaar needs to write to HID devices for receivers and devices.
To be able to do this without running as root requires a udev rule
that gives seated users write access to the HID devices for Logitech receiver and devices.

You can install this rule by copying, as root,
`rules.d/42-logitech-unify-permissions.rules` from Solaar to
`/etc/udev/rules.d`.
You will probably also have to tell udev to reload its rule via
`sudo udevadm control --reload-rules`.

For this rule to set up the correct permissions for your receivers and devices
you will then need to either disconnect your receivers and
any USB-connected or Bluetooth-connected devices and
re-connect them or reboot your computer.

## Running from the Download Directories

To run Solaar from the download directories, first install the Solaar udev rule if necessary.
Then cd to the solaar directory and run `bin/solaar` for the GUI
or `bin/solaar <command> <arguments>` for the CLI.

Do not run Solaar as root, you may encounter problems with X11 integration and with the system tray.

## Installing Solaar Using Pip

Python programs are usually installed using [pip][pip].
The pip instructions for Solaar are in `setup.py`, the standard place to put such instructions.

To install Solaar for yourself only run `pip install --user .` from the solaar directory.
This tells pip to install into your `.local` directory, but does not install Solaar's udev rule.
(See above for installing the udev rule.)
Once the udev rule has been installed you can then run Solaar as `~/.local/bin/solaar`.

Installing python programs to system directories using pip is generally frowned on both
because this runs arbitrary code as root and because this can override existing python libraries
that other users or even the system depend on. If you want to install solaar to /usr/local run
`sudo bash -c 'umask 022 ; pip install .'` in the solaar directory.
(The umask is needed so that the created files and directories can be read and executed by everyone.)
Then solaar can be run as /usr/local/bin/solaar.
You will also have to install the udev rule.

[pip]: https://en.wikipedia.org/wiki/Pip_(package_manager)

## Solaar in other languages

If you want to have Solaar's user messages in some other language you need to run
`tools/po-compile.sh` to create the translation files before running or installing Solaar
and set the LANGUAGE environment variable appropriately when running Solaar.

## Running Solaar at Startup

Distributions can cause Solaar can be run automatically at user login by installing a desktop file at
`/etc/xdg/autostart/solaar.desktop`. An example of this file content can be seen in the repository at
[share/autostart/solaar.desktop](https://github.com/pwr-Solaar/Solaar/blob/master/share/autostart/solaar.desktop).

If you install Solaar yourself you may need to create or modify this file or install a startup file under your home directory.

## Installing from PyPI

As an alternative to downloading and installing you can install the most recent release
(but not the current github version) of Solaar from PyPI.
Just run `pip install --user solaar`.
This will not install the Solaar udev rule, which you will need to copy from
`~/.local/share/solaar/udev-rules.d/42-logitech-unify-permissions.rules`
to `/etc/udev/rules.d` as root.
