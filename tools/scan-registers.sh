#!/bin/sh

if test -z "$1"; then
	echo "Use: $0 <device number 1..6> [<receiver device>]"
	exit 2
fi

HC="$(dirname "$(readlink -f "$0")")/hidconsole"
if test "$1" = "FF"; then
	DEVNUMBER=FF
else
	DEVNUMBER=0$1
fi
HIDRAW=$2

z='0 1 2 3 4 5 6 7 8 9 a b c d e f'
do_req() {
	"$HC" --hidpp $HIDRAW | grep -v "\[1. $DEVNUMBER 8F.. ..0[12]" | grep -B 1 '^>> '
}

oldflags=$(echo "10 ${DEVNUMBER} 8100 000000" | do_req | grep -Po "^>> \([0-9. ]*\) \[10 $DEVNUMBER 8100 \K[0-9a-f]{6}(?=\])")
if [ -n "$oldflags" ]; then
	echo "# Old notification flags: $oldflags"
	{
		echo "10 ${DEVNUMBER} 8000 ffffff"     # enable all notifications
		echo "10 ${DEVNUMBER} 8100 000000"     # read available notifs
		echo "10 ${DEVNUMBER} 8000 $oldflags"  # restore notifications
	} | do_req | grep -B 1 "^>>.* $DEVNUMBER 8100 "
else
	echo "# Failed to read notification flags."
fi

for x in $z; do
	for y in $z; do
		[ "$x$y" = 00 ] || \
		echo "10 ${DEVNUMBER} 81${x}${y} 000000"
	done
done | do_req

for x in $z; do
	for y in $z; do
		echo "10 ${DEVNUMBER} 83${x}${y} 000000"
	done
done | do_req
