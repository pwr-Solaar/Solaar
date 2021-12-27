---
title: Solaar
layout: default
---

**Solaar** is a Linux manager for many Logitech keyboards, mice, and trackpads
that connect wirelessly to a USB [Unifying][unifying], Bolt, Lightspeed, or Nano receiver,
connect directly via a USB cable, or connect via Bluetooth.
Solaar does not work with peripherals from other companies.

Documentation here is for the current version of Solaar.
Some Linux distributions distribute old versions of Solaar.
If you are using an old version and something described here does not work you should upgrade
using one of the methods described below.

Solaar can be used as a GUI application or via its command-line interface.
Both interfaces are able to list the connected devices and
show information about each device, often including battery status.
Solaar is able to pair and unpair devices with
receivers as supported by the device and receiver.
Solaar can also control some changeable features of devices,
such as smooth scrolling or function key behavior.
Solaar keeps track of these changed settings on a per-computer basis and the GUI application restores them whenever a device connects.
(Devices forget most settings when powered down.)
For more information on how to use Solaar see
[the usage page](https://pwr-solaar.github.io/Solaar/usage),
and for more information on its capabilities see
[the capabilities page](https://pwr-solaar.github.io/Solaar/capabilities).


Solaar's GUI normally uses an icon in the system tray and starts with its main window visible.
This aspect of Solaar depends on having an active system tray, which is not the default
situation for recent versions of Gnome.  For information on to set up a system tray under Gnome see
[the capabilities page](https://pwr-solaar.github.io/Solaar/capabilities).

Solaar's GUI can be started in several ways

- `--window=show` (the default) starts with its main window visible,
- `--window=hide` starts with its main window hidden,
- `--window=only` does not use the system tray, and starts with main window visible.

For more information on Solaar's command-line interface use the help option,
as in `solaar --help`.

Solaar does not process normal input from devices. It is thus unable
to fix problems that arise from incorrect handling of mouse movements or keycodes
by Linux drivers or other software.

Solaar has progressed past version 1.0. Problems with earlier versions should
not be reported as bugs. Instead, upgrade to a recent version or manually install
the current version from [GitHub](https://github.com/pwr-Solaar/Solaar).
Some capabilities of Solaar have been developed by observing the behavior of
Logitech receivers and devices and generalizing from these observations.
If your Logitech receiver or device behaves strangely this may be caused by
an incorrect behavior generalization.
Please report such experiences by creating an issue in
[the Solaar repository](https://github.com/pwr-Solaar/Solaar/issues).

[unifying]: https://en.wikipedia.org/wiki/Logitech_Unifying_receiver


## Supported Devices

Solaar will detect all devices paired with supported Unifying, Bolt, Lightspeed, or Nano
receivers, and at the very least display some basic information about them.
Solaar will detect some Logitech devices that connect via a USB cable or Bluetooth.

Solaar can pair and unpair a Logitech device showing the Unifying logo
(Solaar's version of the [logo][logo])
with any Unifying receiver,
and pair and unpair a Logitech device showing the Bolt logo
with any Bolt receiver,
and
can pair and unpair Lightspeed devices with Lightspeed receivers for the same model.
Solaar can pair some Logitech devices with Logitech Nano receivers but not all Logitech
devices can be paired with Nano receivers.
Logitech devices without a Unifying or Bolt logo
generally cannot be paired with Unifying or Bolt receivers.

Solaar does not handle connecting or disconnecting via Bluetooth,
which is done using the usual Bluetooth mechanisms.

For a partial list of supported devices
and their features, see [the devices page](https://pwr-solaar.github.io/Solaar/devices).

[logo]: https://pwr-solaar.github.io/Solaar/assets/solaar.svg

## Prebuilt packages

Up-to-date prebuilt packages are available for some Linux distros
(e.g., Fedora 33+) in their standard repositories.
If a recent version of Solaar is not
available from the standard repositories for your distribution you can try
one of these packages.

- Arch solaar package in the [community repository][arch]
- Ubuntu/Kubuntu 16.04+: use the solaar package from [universe repository][universe repository]
- Ubuntu/Kubuntu stable packages: use the [Solaar stable ppa][ppa2], courtesy of [gogo][ppa4]
- Ubuntu/Kubuntu git build packages: use the [Solaar git ppa][ppa1], courtesy of [gogo][ppa4]
- a [Gentoo package][gentoo], courtesy of Carlos Silva and Tim Harder
- a [Mageia package][mageia], courtesy of David Geiger

Solaar uses a standard system tray implementation; solaar-gnome3 is no longer required for gnome or unity integration.

[ppa4]: https://launchpad.net/~trebelnik-stefina
[ppa2]: https://launchpad.net/~solaar-unifying/+archive/ubuntu/stable
[ppa1]: https://launchpad.net/~solaar-unifying/+archive/ubuntu/ppa
[ppa]: http://launchpad.net/~daniel.pavel/+archive/solaar
[arch]: https://www.archlinux.org/packages/community/any/solaar/
[gentoo]: https://packages.gentoo.org/packages/app-misc/solaar
[mageia]: http://mageia.madb.org/package/show/release/cauldron/application/0/name/solaar
[universe repository]: http://packages.ubuntu.com/search?keywords=solaar&searchon=names&suite=all&section=all

## Manual installation

See [the installation page](https://pwr-solaar.github.io/Solaar/installation)
for the step-by-step procedure for manual installation.

## Known Issues

- If some icons appear broken in the application, make sure you've properly
  configured the Gtk theme and icon theme in your control panel.

- Solaar normally uses icon names for its icons, which in some system tray implementatations
  results in missing or wrong-sized icons.
  The `--tray-icon-size` option forces Solaar to use icon files of appropriate size
  for tray icons instead, which produces better results in some system tray implementatations.
  To use icon files close to 32 pixels in size use `--tray-icon-size=32`.

- The icon in the system tray can show up as 'black on black' in dark
  themes or as non-symbolic when the theme uses symbolic icons.  This is due to problems
  in some system tray implementations. Changing to a different theme may help.
  The `--battery-icons=symbolic` option can be used to force symbolic icons.

- Sometimes the system tray icon does not show up.  The cause of this is unknown.
  Either wait a while and try again or try with the `--window=hide` option.

- Running the command-line application while the GUI
  application is also running *may* occasionally cause either of them to become
  confused about the state of the devices.

- Some Linux drivers view or modify the setting Scroll Wheel Resolution to
  implement smooth scrolling.  If Solaar changes this setting after the driver is
  set up scrolling can be either very fast or very slow.  To fix this problem
  click on the icon at the right edge of the setting to set it to
  "Ignore this setting".
  The mouse has to be reset (e.g., by turning it off and on again) before this fix will take effect.

- Many gaming mice and keyboards have both the ONBOARD PROFILES feature and the REPORT RATE feature.
  On these devices changing the Polling Rate setting requires modifying a setting in
  the ONBOARD PROFILES feature, which can modify how the device works.  Changing the
  Polling Rate setting to "Ignore this setting" (see above) prevents Solaar from
  modifying the ONBOARD PROFILES feature.
  The device has to be reset (e.g., by turning it off and on again) before this fix will take effect.


## License

This software is distributed under the terms of the
[GNU Public License, v2](COPYING).

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
- [Peter Wu](https://lekensteyn.nl/logitech-unifying.html)
- [Nestor Lopez Casado](http://drive.google.com/folderview?id=0BxbRzx7vEV7eWmgwazJ3NUFfQ28)
provided some more Logitech specifications for the HID++ protocol

Also, thanks to Douglas Wagner, Julien Gascard, and Peter Wu for helping with
application testing and supporting new devices.
