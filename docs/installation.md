---
title: Manual Installation
layout: page
---

# Manual installation

## Downloading

Clone Solaar from GitHub by `git clone https://github.com/pwr-Solaar/Solaar.git`

## Requirements for Solaar

Installing Solaar from a repository should have set up all these requirements
so in this situation you should be able to skip this section.

Solaar needs a reasonably new kernel (5.2+ should work fine and recent CentOS distributions are likely to work),
with kernel modules `hid-logitech-dj`
and `hid-logitech-hidpp` loaded. Also, the `udev` package must be installed
and its daemon running. If you have a recent Linux distribution, you are
most likely good to go.

Solaar requires Python 3.6+ and the
`python3-pyudev` package.
The Solaar GUI requires the
`python3-psutil`, `python3-xlib`, and `python3-pyyaml` packages.
To run the GUI Solaar also requires Gtk3 and its GObject introspection bindings.
The Debian/Ubuntu packages that need to be installed are
`python3-gi` and `gir1.2-gtk-3.0`;
in Fedora you need `gtk3` and `python3-gobject`;
if you're using another
distribution the required packages are most likely named something similar.
You may have to install `gcc` and the Python development package (`python3-dev` or `python3-devel`,
depending on your distribution).

If desktop notifications bindings are also installed
(`gir1.2-notify-0.7` for Debian/Ubuntu),
you will also see desktop notifications when devices come online/go offline.
For GNOME Shell/Budgie Desktop/KDE/XFCE support, you also need to have
`gir1.2-ayatanaappindicator3-0.1` installed in Debian/Ubuntu. Although it is
recommended to install and use `gir1.2-ayatanaappindicator3-0.1` if it is
available, you can also use `gir1.2-appindicator3-0.1` if necessary (e.g.,
for Unity in Ubuntu).

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

You only need to install Solaar's udev rule if it is not already installed
on your system or the rule has changed.

## Running from the Download Directories

If the latest Solaar udev rule is installed,
you can just go to the solaar directory and run `bin/solaar` for the GUI
or `bin/solaar <command> <arguments>` for the CLI.

Otherwise, you will need to run Solaar as root via
`sudo bin/solaar` for the GUI
or `sudo bin/solaar <command> <arguments>` for the CLI.

Warning: Running Solaar as root may result in problems with the Solaar icon in the system tray.

## Installing Solaar

Python programs are usually installed using [pip][pip].
The pip instructions for solaar are in `setup.py`, the standard place to put such instructions.

To install solaar for yourself only run `pip install --user .` from the solaar directory.
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
`/etc/xdg/autostart/solaar.desktop`.

If you install Solaar yourself you may need to create or modify this file or install a startup file under your home directory.

## Installing from PyPI

As an alternative to downloading and installing you can install the most recent release
(but not the current github version) of Solaar from PyPI.
Just run `pip install --user solaar`.
This will not install the Solaar udev rule, which you will need to copy from
`~/.local/share/solaar/udev-rules.d/42-logitech-unify-permissions.rules`
to `/etc/udev/rules.d` as root.
