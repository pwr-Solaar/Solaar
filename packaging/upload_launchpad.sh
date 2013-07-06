#!/bin/sh

set -e

export DEBSIGN_KEYID=07D8904B
export DEBMAIL="daniel.pavel+launchpad@gmail.com"

export DISTRIBUTION=ubuntu
export DIST_RELEASE=precise
export DEBIAN_FILES_EXTRA="$PWD/packaging/ubuntu"
export BUILD_EXTRA=ppa1

Z="$(readlink -f "$(dirname "$0")")"
"$Z"/build_deb.sh -S

cd "$Z/../dist/ubuntu/"
/usr/bin/dput --config="$Z/dput.cf" solaar-snapshots-ppa solaar_*_source.changes
