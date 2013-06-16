#!/bin/sh

set -e

Z=$(readlink -f "$0")

RULES_D=/etc/udev/rules.d
if ! test -d "$RULES_D"; then
	echo "$RULES_D not found; is udev installed?"
	exit 1
fi

RULE=42-logitech-unify-permissions.rules

if test -n "$1"; then
	SOURCE="$1"
else
	SOURCE="$(dirname "$Z")/$RULE"
	REALUSER="${SUDO_USER-$USER}"
	if [ -z "$REALUSER" -o "$REALUSER" = "root" ]; then
		: # ignore unknown and root user
	else
		GROUP=plugdev
		TEMP_RULE="$(mktemp --tmpdir "ltudev.XXXXXXXX")"
		sed -e "/^#MODE.*\"plugdev\"/s/^#//" "$SOURCE" > "$TEMP_RULE"
		if ! id -G -n "$REALUSER" | grep -q -F plugdev; then
			GROUP="$(id -g -n "$REALUSER")"
			if getent group plugdev >/dev/null; then
				printf "User '%s' does not belong to the 'plugdev' group, " "$REALUSER"
			else
				printf "Group 'plugdev' does not exist, "
			fi
			echo "will use group '$GROUP' in the udev rule."
			sed -i -e "s/\"plugdev\"/\"$GROUP\"/" "$TEMP_RULE"
		fi
		SOURCE="$TEMP_RULE"
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
install -m 644 "$SOURCE" "$RULES_D/$RULE"

echo "Done. Now remove the Unfiying Receiver and plug it in again."
