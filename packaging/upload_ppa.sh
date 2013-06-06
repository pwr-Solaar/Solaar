#!/bin/sh

set -e

cd "$(dirname "$0")"

./build_ppa.sh -S

dput solaar-snapshots-ppa solaar_*_source.changes
