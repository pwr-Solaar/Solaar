---
title: Manual Installation
layout: page
---

# Manual installation


## Downloading

Clone solaar from GitHub via `git clone https://github.com/pwr-Solaar/Solaar.git`


## Requirements for running Solaar

Installing Solaar from a repository should have set up all these requirements
so in this situation you should be able to skip this section.

Solaar needs a reasonably new kernel (5.0+ should work fine), with kernel modules `hid-logitech-dj`
and `hid-logitech-hidpp` loaded.   Also, the `udev` package must be installed
and its daemon running.  If you have a recent Linux distribution, you are
most likely good to go.

Solaar requires Python 3.2+
and the `python3-pyudev` package. 
To run the GUI, solaar also requires Gtk3, and its GObject
introspection bindings.
The Debian/Ubuntu packages that need to be installed are
`python3-gi` and `gir1.2-gtk-3.0`;
in Fedora you need  `gtk3` and `python3-gobject`;
if you're using another
distribution the required packages are most likely named something similar.

If the desktop notifications bindings are also installed
(`gir1.2-notify-0.7` for Debian/Ubuntu),
you will also get desktop notifications when devices come online/go offline.
For GNOME Shell/Budgie Desktop/KDE/XFCE support, you also need to have
`gir1.2-ayatanaappindicator3-0.1` installed in Debian/Ubuntu. Although it is
recommended to install and use `gir1.2-ayatanaappindicator3-0.1` if it is
available, you can also use `gir1.2-appindicator3-0.1` if necessary (e.g.,
for Unity in Ubuntu).


### Installing Solaar's udev Rule

Solaar needs to write to the receiver's HID device.
To be able to do this without running as root requires udev rule
that gives seated users write access to the HID devices for Logitech receivers.

You can install this rule by copying, as root, 
`rules.d/42-logitech-unify-permissions.rules` from Solaar to
`/etc/udev/rules.d`.
The udev daemon will automatically pick up this file using inotify.

For this rule to set up the correct permissions for your receiver
you will then need to either physically remove the receiver and
re-insert it or reboot your computer.


## Running from the Download Directories

If Solaar's udev rule is installed,
you can just go to the solaar directory and run `bin/solaar` for the GUI
or `bin/solaar <command> <arguments>` for the CLI.

Otherwise you will need to run Solaar as root via
and `sudo bin/solaar` for the GUI
or `sudo bin/solaar <command> <arguments>` for the CLI.


## Installing Solaar

Python programs are usually installed using [pip][pip].
The pip instructions for solaar are in `setup.py`, the standard place to put such instructions.

To install solaar for yourself only run `pip install --user .` from the solaar directory.
This tells pip to install into your `.local` directory, but does not install Solaar's udev rule.
(See above for installing the udev rule.)
You can then run solaar as `sudo ~/.local/bin/solaar` (or just `~/.local/bin/solaar`
if the udev rule has been installed).

Installing python programs to system directories using pip is generally frowned on both
because this runs arbitrary code as root and because this can override existing python libraries
that other users or even the system depend on.  If you want to install solaar to /usr/local run
`sudo bash -c 'umask 022 ; pip install .'` in the solaar directory.
(The umask is needed so that the created files and directories can be read and executed by everyone.)
This will also install the udev rule and the Solaar autostart desktop file.
Then solaar can be run as /usr/local/bin/solaar.

[pip]: https://en.wikipedia.org/wiki/Pip_(package_manager)


## Running Solaar at Startup

Solaar is run automatically at user login via the desktop file
`/etc/xdg/autostart/solaar.desktop`.

If you install Solaar yourself you may need to create or modify this file.


## Using PyPI

As an alternative to downloading and installing you can install a recent release 
(but not the current github version) of Solaar from PyPI.  
Just run `pip install --user solaar` or `sudo pip install solaar`.
The `--user` install will not install the Solaar udev rule or the Solaar autostart file.
