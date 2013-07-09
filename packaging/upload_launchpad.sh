#!/bin/sh

set -e

export DEBCHANGE_VENDOR=ubuntu
export DISTRIBUTION=precise

export DEBFULLNAME='Daniel Pavel'
export DEBEMAIL='daniel.pavel+launchpad@gmail.com'
export DEBSIGN_KEYID=07D8904B

Z="$(readlink -f "$(dirname "$0")")"
"$Z"/build_deb.sh --rebuild "$@"

read -p 'Version: ' VERSION
test "$VERSION"
CHANGES_FILE="$Z/../dist/solaar_${VERSION}_source.changes"
test -r "$CHANGES_FILE"

/usr/bin/dput --config="$Z/dput.cf" solaar-snapshots-ppa "$CHANGES_FILE"
