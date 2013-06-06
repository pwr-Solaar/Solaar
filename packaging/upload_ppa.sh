#!/bin/sh

set -e

cd "$(dirname "$0")"/..
pwd

./packaging/build_ppa.sh -S

cd ./dist/ubuntu/
dput solaar-snapshots-ppa solaar_*_source.changes
