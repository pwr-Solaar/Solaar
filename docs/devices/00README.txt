Files in this directory are edited output from `solaar show` providing
information about devices and receivers that Solaar supports.  This
directory does not contain information about all devices and receivers that
Solaar supports.  Information is generally only added when provided in a
Solaar issue.

Directions for constructing the files are given below.  The files
  Unifying Receiver C52B.txt
  Craft Advanced Keyboard 4066.txt
  Craft Advanced Keyboard B350.txt
  MX Master 3 Wireless Mouse 4082.txt
  MX Master 3 Wireless Mouse B023.txt
are good examples of following the directions below.


File Naming

Logitech device names are often reused so the names of files can't just be
the device name.  File names start with the name of the device or receiver
as given in the first line of of output for the device.  The file name
continues with a space and the WPID, if the device is connected to a
receiver, or the second half of the USB ID, if the device is connected via
USB or Bluetooth.  The WPID or USB ID are in upper case.  As devices can
behave differently when connected via a receiver or USB or Bluetooth there
should be a file for each possible connection method.

Files that do not follow this naming convention are retained for historical purposes.


File Contents

Each file should start with the Solaar version as given in the first line of
output from `solaar show` and a blank line.  Next is the output of `solaar
show` for the device or receiver. The output of `solaar show` can be edited
to remove serial numbers and variable information such as the current values
of settings.  For older devices probes of the device registers should be
included but for newer devices this should not be necessary.

Unifying receivers can pair with any device that has the Unifying logo.
Bolt receivers can pair with any device that has the Bolt logo.
Nano and Lightspeed receivers can only pair with certain devices,
so the end of their files should contain device WPIDs that they have
been seen to be paired with or are part of.


Updating Files

Newer versions of Solaar add support for more settings so it is useful to
provide updated versions of these files if there is information from the
current version of `solaar show` that is not in the existing file.
