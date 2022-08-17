Files in this directory are edited output from `solaar show` providing
information about devices and receivers that Solaar supports.  Directions
for constructing the files are given below.  The files
  Unifying Receiver C52B.txt
  Craft Advanced Keyboard 4066.txt
  Craft Advanced Keyboard B350.txt
  MX Master 3 Wireless Mouse 4082.txt
  MX Master 3 Wireless Mouse B023.txt
are good examples of following the directions below.


File Naming

Logitech device names are often reused so the names of files can't just be
the device name.  File names start with the name of the device or receiver as
given in the first line of of output for the device.  The file name continues
with a space and the WPID, if the device is connected to a receiver, or the
second half of the USB id, if the device is connected via USB or Bluetooth.
As devices can behave differently when connected via a receiver or USB or
Bluetooth there should be a file for each possible connection method.

Files that do not follow this naming convention are retained for historical purposes.


File Contents

Each file should start with the Solaar version as given in the first line of
output from `solaar show` and a blank line.  The rest of the file is the
output of `solaar show` for the device or receiver. The output of `solaar
show` can be edited to remove serial numbers and variable information such as
the current values of settings.


Updating Files

Newer versions of Solaar add support for more settings so it is useful to provide updated
versions of these files if there is information from the current version of `solaar show`
that is not in the existing file.
