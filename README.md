**Solaar** is a Linux device manager for Logitech's
[Unifying Receiver](http://www.logitech.com/en-us/66/6079) peripherals.

It comes in two flavours, command-line and GUI.  Both are able to list the
devices paired to a Unifying Receiver, show detailed info for each device, and
also pair/unpair supported devices with the receiver.


Requirements
------------

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


Installation
------------

Normally USB devices are not accessible for r/w by regular users, so you will
need to do a one-time udev rule installation to allow access to the Logitech
Unifying Receiver.

In the `rules.d/` folder of Solaar you'll find a udev rule file, to be copied in
`/etc/udev/rules.d/` (as the root user).

In its current form it makes the Unifying Receiver device available for r/w by
all users belonging to the `plugdev` system group (standard Debian/Ubuntu group
for pluggable devices). It may need changes, specific to your particular
system's configuration.

If in doubt, replacing `GROUP="plugdev"` with `GROUP="<your username>"` should just
work.

After you copy the file to `/etc/udev/rules.d` (and possibly modify it for your
system), run `udevadm control --reload-rules` as root for it to apply. Then
physically remove the Unifying Receiver, wait 10 seconds and re-insert it.


Supported Devices
-----------------

**Solaar** will detect all devices paired with your Unifying Receiver, and at
the very least display some basic information about them.  Depending on the
device, it may be able to read its battery status.  Changing various settings
of the devices (like mouse DPI) is currently not supported, but implementation
is planned.

The [K750 Solar Keyboard](http://www.logitech.com/keyboards/keyboard/devices/7454)
is also queried for its solar charge status.  Pressing the Solar key on the
keyboard will pop-up the application window and display the current lighting
value, similar to Logitech's Solar app for Windows.

Extended support for other devices will be added in the future, depending on the
documentation available, but the K750 keyboard is the only device I have and can
test on right now.


Thanks
------

This project began as a third-hand clone of [Noah K. Tilton](https://github.com/noah)'s
logitech-solar-k750 project on GitHub (no longer available). It was developed
further thanks to the diggings in Logitech's HID++ protocol done by many other
people:

- [Julien Danjou](http://julien.danjou.info/blog/2012/logitech-k750-linux-support),
who also provided some internal
[Logitech documentation](http://julien.danjou.info/blog/2012/logitech-unifying-upower)
- [Lars-Dominik Braun](http://6xq.net/git/lars/lshidpp.git)
- [Alexander Hofbauer](http://derhofbauer.at/blog/blog/2012/08/28/logitech-performance-mx)
- [Clach04](http://bitbucket.org/clach04/logitech-unifying-receiver-tools)
