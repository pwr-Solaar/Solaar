#!/bin/sh

cd `dirname "$0"`/..
DEBIAN="$PWD/packaging/debian"
RULES_D="$PWD/rules.d"

DIST="${TMPDIR:-/tmp}/$PWD"
mkdir -m 0700 -p "$DIST"
rm -rf "$DIST"/*
python setup.py sdist --dist-dir="$DIST"

cd "$DIST"
S=`ls -1 solaar-*.tar.gz`
VERSION=${S#solaar-}
VERSION=${VERSION%.tar.gz}
tar xfz "$S"
mv "$S" solaar_$VERSION.orig.tar.gz

cd solaar-*
cp -a "$DEBIAN" .

for rule in "$RULES_D"/*.rules; do
	target=`basename "$rule"`
	target=${target##??-}
	target=${target%%.rules}
	cp -av "$rule" ./debian/solaar.$target.udev
done

debuild -uc -us
