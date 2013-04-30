**Solaar** is a Linux device manager for Logitech's [Unifying Receiver][unifying]
peripherals. It is able to pair/unpair devices to the receiver, and for most
devices read battery status.

It comes in two flavors, command-line and GUI.  Both are able to list the
devices paired to a Unifying Receiver, show detailed info for each device, and
also pair/unpair supported devices with the receiver.


## Supported Devices

**Solaar** will detect all devices paired with your Unifying Receiver, and at
the very least display some basic information about them.

For some devices, extra settings (usually not available through the standard
Linux system configuration) are supported:

* The [K750 Solar Keyboard][K750] is also queried for its solar charge status.
  Pressing the `Solar` key on the keyboard will pop-up the application window
  and display the current lighting value (Lux) as reported by the keyboard,
  similar to Logitech's *Solar.app* for Windows.

* The state of the `FN` key can be toggled on some keyboards ([K750][K750],
  [K800][K800] and [K360][K360]). It changes the way the function keys
  (`F1`..`F12`) work, i.e. whether holding `FN` while pressing the function keys
  will generate the standard `Fx` keycodes or the special function (yellow
  icons) keycodes.

* The DPI can be changed on the [Performance MX Mouse][P_MX].

* Smooth scrolling (higher sensitivity on vertical scrolling with the wheel) can
  be toggled on the [M705 Marathon Mouse][M705] and [Anywhere MX Mouse][A_MX].

Extended support for other devices may be added in the future, depending on the
documentation available, but the K750 keyboard and M705 mouse are the only
devices I have and can directly test on right now.


## Pre-built packages

Pre-built packages are available for a few Linux distros:

* Ubuntu 12.04+: [ppa:daniel.pavel/solaar][ppa]
* a Debian/sid package: [.deb][debian]
* a [Gentoo overlay][gentoo], courtesy of Carlos Silva
* an [OpenSUSE rpm][opensuse], courtesy of Mathias Homann
* an [Arch package][arch], courtesy of Arnaud Taffanel

[ppa]: http://launchpad.net/~daniel.pavel/+archive/solaar
[debian]: http://pwr.github.com/Solaar/packages/solaar_0.8.7-1_all.deb
[gentoo]: http://code.r3pek.org/gentoo-overlay/src
[opensuse]: http://software.opensuse.org/package/Solaar
[arch]: http://aur.archlinux.org/packages/solaar

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


## Known Issues

- Ubuntu's Unity indicators are not supported at this time. However, if you
  whitelist 'Solaar' in the systray, you will get an icon (see
  [Enable more icons to be in the system tray?][ubuntu_systray] for details).

[ubuntu_systray]: http://askubuntu.com/questions/30742

- The application only looks at the first Unifying Receiver it finds, even if
  there's more than one plugged in. Support for multiple receivers is in
  progress.

- Devices connected throught a [Nano Receiver][nano] (which is very similar to
  the Unifying Receiver) are not supported at this time.

- Running the command-line application (`bin/solaar-cli`) while the GUI
  application is also running *may* occasionally cause either of them to become
  confused about the state of the devices. I haven't encountered this often
  enough to be able to be able to diagnose it properly yet.


## Thanks

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

Also thanks to Douglas Wagner and Julien Gascard for helping with application
testing and supporting new devices.

--

[unifying]: http://logitech.com/en-us/66/6079
[nano]: http://logitech.com/mice-pointers/articles/5926
[K750]: http://logitech.com/product/k750-keyboard
[K800]: http://logitech.com/product/wireless-illuminated-keyboard-k800
[K360]: http://logitech.com/product/keyboard-k360
[M705]: http://logitech.com/product/marathon-mouse-m705
[P_MX]: http://logitech.com/product/performance-mouse-mx
[A_MX]: http://logitech.com/product/anywhere-mouse-mx
