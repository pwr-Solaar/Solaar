#!/bin/sh

cd `dirname "$0"`/..
./tools/build_deb.sh -S -sa

cd dist
sed -e 's/UNRELEASED/precise/g' -i solaar_*_source.changes
debsign --re-sign solaar_*_source.changes
dput solaar-ppa solaar_*_source.changes
