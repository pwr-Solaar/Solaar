#!/bin/sh

set -e

cd "$(dirname "$0")"/..
./packaging/build_ppa.sh -S

cd ./dist/ubuntu/

C=${XDG_CONFIG_HOME:-$HOME/.config}/debian/dput.cf
if test -r "$C"; then
	C="--config $C"
elif test -r "$HOME/.dput.cf"; then
	C="--config=$HOME/.dput.cf"
else
	unset C
fi
/usr/bin/dput $C solaar-snapshots-ppa solaar_*_source.changes
