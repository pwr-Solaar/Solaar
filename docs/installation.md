# Manual installation

### Requirements

You should have a reasonably new kernel (3.2+), with the `logitech-djreceiver`
driver enabled and loaded (kernel module `hid-logitech-dj`) or Linux 3.19+
(kernel module `hid-logitech-hidpp`); also, the `udev` package must be installed
and the daemon running.  If you have a modern Linux distribution (2011+), you're
most likely good to go.

The command-line application (`bin/solaar-cli`) requires Python 2.7.3 or 3.2+
(either version should work), and the `python-pyudev`/`python3-pyudev` package.

The GUI application (`bin/solaar`) also requires Gtk3, and its GObject
Introspection bindings. The Debian/Ubuntu package names are
`python-gi`/`python3-gi` and `gir1.2-gtk-3.0`; if you're using another
distribution the required packages are most likely named something similar.
If the desktop notifications bindings are also installed (`gir1.2-notify-0.7`),
you will also get desktop notifications when devices come online/go offline.

For gnome-shell/Unity support, you also need to have `gir1.2-appindicator3-0.1`
installed.


### Installation

Normally USB devices are not accessible for r/w by regular users, so you will
need to do a one-time udev rule installation to allow access to the Logitech
Unifying Receiver.

You can run the `rules.d/install.sh` script from Solaar to do this installation
automatically (make sure to run it as your regular desktop user, it will switch
to root when necessary), or you can do all the required steps by hand, as the
root user:

1. Copy `rules.d/99-logitech-unifying-receiver.rules` from Solaar to
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
   `gpasswd <desktop username> plugdev`. If these users were not assigned to the
   group before, they must re-login for the changes to take effect.
