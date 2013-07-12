#!/bin/sh

set -e

export DEBCHANGE_VENDOR=ubuntu
export DISTRIBUTION=precise

export DEBFULLNAME='Daniel Pavel'
export DEBEMAIL='daniel.pavel+launchpad@gmail.com'
export DEBSIGN_KEYID=07D8904B

Z="$(readlink -f "$(dirname "$0")")"
"$Z"/build_deb.sh --rebuild "$@"

cd "$Z/../dist"
CHANGES_FILE=$(/bin/ls --format=single-column --sort=time solaar_*_source.changes | /usr/bin/head --lines=1)
/usr/bin/dput --config="$Z/dput.cf" solaar-snapshots-ppa "$CHANGES_FILE"
