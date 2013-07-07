#!/bin/sh

set -e

export DEBCHANGE_VENDOR=debian
export DISTRIBUTION=unstable

export DEBFULLNAME='Daniel Pavel'
export DEBEMAIL='daniel.pavel+debian@gmail.com'
export DEBSIGN_KEYID=0B34B1A7

Z="$(readlink -f "$(dirname "$0")")"
"$Z"/build_deb.sh --release "$@"

/usr/bin/dput --config="$Z/dput.cf" mentors \
	"$Z/../dist/debian"/solaar_*_source.changes
