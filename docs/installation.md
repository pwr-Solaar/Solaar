---
title: Manual Installation
layout: page
---

# Manual installation


### Requirements

You should have a reasonably new kernel (4.0+), with kernel modules `hid-logitech-dj`
and `hid-logitech-hidpp` loaded.   Also, the `udev` package must be installed
and the daemon running.  If you have a recent Linux distribution (2017+), you are
most likely good to go.

Solaar requires Python 3.2+
and the `python3-pyudev` package. 
To run the GUI, solaar also requires Gtk3, and its GObject
Introspection bindings. The Debian/Ubuntu package names are
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


### Downloading

Clone solaar from GitHub via `git clone https://github.com/pwr-Solaar/Solaar.git`


### Running from the Download Directories

To access the USB devices you may need to run solaar as super user.
Go to the solaar directory and `sudo bin/solaar` for the GUI
or `sudo bin/solaar <command> <arguments>` for the CLI.

If you are running a security-enhanced Linux (RedHat or Fedora)
you may have to turn off enforcing mode.


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

Then solaar can be run without using sudo.


### Installing Solaar

Python programs are usually installed using [pip][pip].
The pip instructions for solaar are in `setup.py`, the standard place to put such instructions.

To install solaar for yourself only run `pip install --user .` from the solaar directory.
This tells pip to install into your `.local` directory. You can then run solaar as 
 `~/.local/bin/solaar`.

Installing python programs to system directories using pip is generally frowned on both
because this runs arbitrary code as root and because this can override existing python libraries
that other users or even the system depend on.  If you want to install solaar to /usr/local run
`sudo bash -c 'umask 022 ; pip install .'` in the solaar directory.
(The umask is needed so that the created files and directories can be read and executed by everyone.)
This will also install the udev rule and the Solaar autostart desktop file.
Then solaar can be run as /usr/local/bin/solaar.

[pip]: https://en.wikipedia.org/wiki/Pip_(package_manager)



### Running Solaar at Startup

Solaar is run automatically at user login using a desktop file,
which may have been installed at `/etc/xdg/autostart/solaar.desktop`.
If you manually install Solaar you may need to modify this automatic starting of Solaar.


### Using PyPI

As an alternative to downloading and installing you can install a recent release 
(but not the current git version) of Solaar from PyPI.  
Just run `pip install --user solaar` or `sudo pip install solaar`.
The `--user` install will not install the Solaar udev rule or the Solaar autostart file.
