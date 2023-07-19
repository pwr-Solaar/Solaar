#!/bin/sh

if test -z "$1"; then
	echo "Use: $0 <device number 1..6> [<receiver device>]"
	exit 2
fi

HC="$(dirname "$(readlink -f "$0")")/hidconsole"
if test "$1" = "FF" -o "$1" = "ff"; then
	DEVNUMBER=FF
else
	DEVNUMBER=0$1
fi
HIDRAW=$2

do_req() {
	"$HC" --hidpp $HIDRAW | grep "^>> " | grep -v "\[1. .. 8F.. "
}

req00="$(mktemp --tmpdir req00-XXXXXX)"
echo "10 ${DEVNUMBER} 8100 000000" | do_req >"$req00"
oldflags=$(grep -Po "^>> \([0-9. ]*\) \[10 ${DEVNUMBER} 8100 \K[0-9a-f]{6}(?=\])" "$req00")
if [ -n "$oldflags" ]; then
	echo "# Old notification flags: $oldflags"
	cat >"$req00-flags" <<-_CHECK_NOTIFICATIONS
		10 ${DEVNUMBER} 8000 ffffff
		10 ${DEVNUMBER} 8100 000000
		10 ${DEVNUMBER} 8000 ${oldflags}
	_CHECK_NOTIFICATIONS
	# set all possible flags, read the new value, then restore the old value
	# this will show all supported notification flags by this device
	cat "$req00-flags" | do_req | grep "^>>.* ${DEVNUMBER} 8100 "
else
	echo "# Warning: hidconsole API got changed - unrecognized output"
	cat "$req00"
fi
rm --force "$req00" "$req00-flags" &

echo SHORT REGISTERS
# read all short registers, skipping 00
for n in $(seq 1 255); do
	printf "10 ${DEVNUMBER} 81%02x 000000\n" $n
done | do_req

echo LONG REGISTERS
# read all long registers
for n in $(seq 0 255); do
	printf "10 ${DEVNUMBER} 83%02x 000000\n" $n
done | do_req

echo PAIRING INFORMAITON # read all pairing information
for n in $(seq 0 255); do
	printf "10 ${DEVNUMBER} 83B5 %02x0000\n" $n
done | do_req
