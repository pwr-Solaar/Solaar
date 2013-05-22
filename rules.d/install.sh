#!/bin/sh

set -e

Z=$(readlink -f "$0")

RULES_D=/etc/udev/rules.d
if ! test -d "$RULES_D"; then
	echo "$RULES_D not found; is udev installed?"
	exit 1
fi

RULE=99-logitech-unifying-receiver.rules

if test -n "$1"; then
	SOURCE="$1"
else
	SOURCE="$(dirname "$Z")/$RULE"
	if ! id -G -n | grep -q -F plugdev; then
		GROUP="$(id -g -n)"
		echo "User '$USER' does not belong to the 'plugdev' group, will use group '$GROUP' in the udev rule."
		TEMP_RULE="${TMPDIR:-/tmp}/$$-$RULE"
		cp -f "$SOURCE" "$TEMP_RULE"
		SOURCE="$TEMP_RULE"
		sed -i -e "s/GROUP=\"plugdev\"/GROUP=\"$GROUP\"/" "$SOURCE"
	fi
fi

if test "$(id -u)" != "0"; then
	echo "Switching to root to install the udev rule."
	test -x /usr/bin/pkexec && exec /usr/bin/pkexec "$Z" "$SOURCE"
	test -x /usr/bin/sudo && exec /usr/bin/sudo -- "$Z" "$SOURCE"
	test -x /bin/su && exec /bin/su -c "\"$Z\" \"$SOURCE\""
	echo "Could not switch to root: none of pkexec, sudo or su were found?"
	exit 1
fi

echo "Installing $RULE."
cp "$SOURCE" "$RULES_D/$RULE"
chmod a+r "$RULES_D/$RULE"

echo "Done. Now remove the Unfiying Receiver and plug it in again."
