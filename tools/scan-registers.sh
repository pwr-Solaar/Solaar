#!/bin/sh

if test -z "$1"; then
	echo "Use: $0 <device number 1..6> [<receiver device>]"
	exit 2
fi

HC="$(dirname "$(readlink -f "$0")")/hidconsole"

z='0 1 2 3 4 5 6 7 8 9 a b c d e f'
do_req() {
	"$HC" --hidpp $2 | grep -v ' 8F.. ..0[12]' | grep -B 1 '^>> '
}

reg00=$(echo "10 0${1} 8100 000000" | do_req)
oldflags=$(echo "$reg00" | grep -Po '>>.*? 8100 \K[0-9a-f]{6}(?=\])')
if [ -n "$oldflags" ]; then
	echo "# Old notification flags: $oldflags"
	{
		echo "10 0${1} 8000 ffffff"     # enable all notifications
		echo "10 0${1} 8100 000000"     # read available notifs
		echo "10 0${1} 8000 $oldflags"  # restore notifications
	} | do_req | grep -B 1 '^>>.* 8100 '
elif [ -n "$reg00" ]; then
	echo "# Warning: hidconsole API got changed - unrecognized output"
	echo "$reg00"
fi

for x in $z; do
	for y in $z; do
		[ "$x$y" = 00 ] || \
		echo "10 0${1} 81${x}${y} 000000"
	done
done | do_req

for x in $z; do
	for y in $z; do
		echo "10 0${1} 83${x}${y} 000000"
	done
done | do_req
