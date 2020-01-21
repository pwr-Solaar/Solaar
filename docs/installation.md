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
`python3-gi` and `gir1.2-gtk-3.0`; if you're using another
distribution the required packages are most likely named something similar.
If the desktop notifications bindings are also installed (`gir1.2-notify-0.7`),
you will also get desktop notifications when devices come online/go offline.

For gnome-shell/Unity support, you also need to have `gir1.2-appindicator3-0.1`
installed.


### Downloading

Clone solaar from GitHub via `git clone https://github.com/pwr-Solaar/Solaar.git`


### Running from the Download Directories

To access the USB devices you may need to run solaar as super user.
Go to the solaar directory and `sudo bin/solaar` for the GUI
or `sudo bin/solaar <command> <arguments>` for the CLI.

If you are running a security-enhanced Linux (RedHat or Fedora)
you may have to turn off enforcing mode.


### Installation

Normally USB devices are not accessible for r/w by regular users, so you will
need to do a one-time udev rule installation to allow access to the Logitech
Unifying Receiver.

You can run the `rules.d/install.sh` script from Solaar to do this installation
automatically (make sure to run it as your regular desktop user, it will switch
to root when necessary), or you can do all the required steps by hand, as the
root user:

1. Copy `rules.d/42-logitech-unifying-receiver.rules` from Solaar to
   `/etc/udev/rules.d/`. The `udev` daemon will automatically pick up this file
   using inotify.

   By default, the rule allows all members of the `plugdev` group to have
   read/write access to the Unifying Receiver device. (standard Debian/Ubuntu
   group for pluggable devices). It may need changes, specific to your
   particular system's configuration. If in doubt, replacing `GROUP="plugdev"`
   with `GROUP="<your username>"` should just work.

2. Physically remove the Unifying Receiver and re-insert it.

   This is necessary because if the receiver is already plugged-in, it already
   has a `/dev/hidrawX` device node, but with the old (`root:root`) permissions.
   Plugging it again will re-create the device node with the right permissions.

3. Make sure your desktop users are part of the `plugdev` group, by running
   `gpasswd -a <desktop username> plugdev`. If these users were not assigned to the
   group before, they must re-login for the changes to take effect.


Then solaar can be run from the download directory without using sudo.

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
Then solaar can be run as /usr/local/bin/solaar.

[pip]: https://en.wikipedia.org/wiki/Pip_(package_manager)