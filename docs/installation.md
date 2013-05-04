## Manual instalation

### Requirements

You should have a reasonably new kernel (3.2+), with the `logitech-djreceiver`
driver enabled and loaded; also, the `udev` package must be installed and the
daemon running.  If you have a modern Linux distribution (2011+), you're most
likely good to go.

The command-line application (`bin/solaar-cli`) requires Python 2.7.3 or 3.2+
(either version should work), and the `python-pyudev`/`python3-pyudev` package.

The GUI application (`bin/solaar`) also requires Gtk3, and its GObject
Introspection bindings. The Debian/Ubuntu package names are
`python-gi`/`python3-gi` and `gir1.2-gtk-3.0`; if you're using another
distribution the required packages are most likely named something similar.
If the desktop notifications bindings are also installed (`gir1.2-notify-0.7`),
you will also get desktop notifications when devices come online/go offline.

### Installation

Normally USB devices are not accessible for r/w by regular users, so you will
need to do a one-time udev rule installation to allow access to the Logitech
Unifying Receiver.

You can run the `rules.d/install.sh` script from Solaar to do this installation
automatically (it will switch to root when necessary), or you can do all the
required steps by hand, as the root user:

1. copy `rules.d/99-logitech-unfiying-receiver.rules` from Solaar to
  `/etc/udev/rules.d/`

  By default, the rule makes the Unifying Receiver device available for r/w by
  all users belonging to the `plugdev` system group (standard Debian/Ubuntu
  group for pluggable devices). It may need changes, specific to your
  particular system's configuration. If in doubt, replacing `GROUP="plugdev"`
  with `GROUP="<your username>"` should just work.

2. run `udevadm control --reload-rules` to let the udev daemon know about the
  new rule

3. physically remove the Unifying Receiver, wait 10 seconds and re-insert it
