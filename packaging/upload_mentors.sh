#!/bin/sh

set -e

Z="$(readlink -f "$(dirname "$0")")"
"$Z"/build_deb.sh -S

cd "$Z/../dist/debian/"
/usr/bin/dput --config="$Z/dput.cf" mentors solaar_*_source.changes
