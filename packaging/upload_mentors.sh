#!/bin/sh

set -e

export DEBCHANGE_VENDOR=debian
export DISTRIBUTION=unstable

export DEBFULLNAME='Daniel Pavel'
export DEBEMAIL='daniel.pavel+debian@gmail.com'
export DEBSIGN_KEYID=0B34B1A7

Z="$(readlink -f "$(dirname "$0")")"
"$Z"/build_deb.sh --release "$@"

read -p 'Version: ' VERSION
test "$VERSION"
CHANGES_FILE="$Z/../dist/solaar_${VERSION}_source.changes"
test -r "$CHANGES_FILE"

/usr/bin/dput --config="$Z/dput.cf" mentors "$CHANGES_FILE"
