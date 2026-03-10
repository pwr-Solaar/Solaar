# Solaar Installation Guide for RHEL / Rocky / AlmaLinux

This guide provides both manual installation steps and an automated installation script for Solaar on Red Hat Enterprise Linux compatible systems.

Supported distributions:

- Red Hat Enterprise Linux (RHEL)
- Rocky Linux
- AlmaLinux
- Oracle Linux
- CentOS Stream

The commands assume a minimal CLI system with sudo access.

---

# 1. Install Required Dependencies

Update the system and install required packages.

sudo dnf update -y

sudo dnf install -y \
python3 \
python3-pip \
python3-devel \
python3-gobject \
python3-dbus \
gtk3 \
libappindicator-gtk3 \
git \
hidapi \
libusb1

Optional but recommended tools:

sudo dnf install -y \
python3-virtualenv \
python3-setuptools

---

# 2. Clone Solaar Repository

Clone the upstream Solaar repository.

git clone https://github.com/pwr-Solaar/Solaar.git

cd Solaar

---

# 3. Install Solaar

Install using pip.

pip3 install .

If installing system-wide:

sudo pip3 install .

---

# 4. Running Solaar

Launch from terminal.

solaar

or

python3 -m solaar

If running a desktop environment, Solaar should appear in the system tray.

---

# 5. Permissions for Logitech Receiver

If the receiver is not detected, add udev rules.

sudo tee /etc/udev/rules.d/42-logitech-unify-permissions.rules <<EOF
SUBSYSTEM=="usb", ATTR{idVendor}=="046d", MODE="0666"
EOF

Reload rules.

sudo udevadm control --reload-rules
sudo udevadm trigger

Reconnect the Logitech receiver.

---

# 6. Automated Installation Script

An automated script is included to simplify installation.

Example usage:

sudo ./install-rhel.sh

The script performs the following actions:

1. Detects the distribution
2. Installs required dependencies
3. Clones the repository if needed
4. Installs Solaar
5. Configures udev permissions
6. Verifies installation

---

# 7. Example Automated Script

Below is a reference automation script.

```

#!/usr/bin/env bash

set -e

echo "Solaar RHEL Installer"

if [[ $EUID -ne 0 ]]; then
echo "Run this script with sudo"
exit 1
fi

echo "Updating system..."
dnf update -y

echo "Installing dependencies..."
dnf install -y 
python3 
python3-pip 
python3-gobject 
gtk3 
libappindicator-gtk3 
git 
hidapi 
libusb1

WORKDIR="/opt/solaar"

if [[ ! -d "$WORKDIR" ]]; then
echo "Cloning repository..."
git clone [https://github.com/pwr-Solaar/Solaar.git](https://github.com/pwr-Solaar/Solaar.git) "$WORKDIR"
fi

cd "$WORKDIR"

echo "Installing Solaar..."
pip3 install .

echo "Configuring Logitech receiver permissions..."

cat <<EOF > /etc/udev/rules.d/42-logitech-unify-permissions.rules
SUBSYSTEM=="usb", ATTR{idVendor}=="046d", MODE="0666"
EOF

udevadm control --reload-rules
udevadm trigger

echo "Installation complete."

echo "Run Solaar using:"
echo "solaar"

```

---

# 8. Verification

Confirm installation.

which solaar

Check version.

solaar --version

---

# 9. Troubleshooting

Receiver not detected:

lsusb | grep Logitech

Restart udev.

sudo udevadm trigger

Check device permissions.

ls -l /dev/hidraw*

---

# 10. Notes

Solaar supports Logitech Unifying and Bolt receivers. Some advanced device features may depend on kernel HID support.

For enterprise deployments, administrators may package Solaar as an RPM or deploy using configuration management tools such as Ansible.
