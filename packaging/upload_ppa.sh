#!/bin/sh

cd `dirname "$0"`/..
./packaging/build_deb.sh -S "$@"

cd dist
sed -e 's/UNRELEASED/precise/g' -i solaar_*_source.changes
debsign --re-sign solaar_*_source.changes
dput -f solaar-ppa solaar_*_source.changes

