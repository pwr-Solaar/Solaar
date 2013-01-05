#!/bin/sh

cd `dirname "$0"`/..
mkdir -p dist
DIST="$PWD/dist"
DEBIAN="$PWD/packaging/debian"
RULES_D="$PWD/rules.d"

BUILD_DIR="${TMPDIR:-/tmp}/$PWD"
mkdir -m 0700 -p "$DIST"
rm -rf "$DIST"/*
python setup.py sdist --dist-dir="$BUILD_DIR"

cd "$BUILD_DIR"
S=`ls -1 solaar-*.tar.gz`
VERSION=${S#solaar-}
VERSION=${VERSION%.tar.gz}
tar xfz "$S"
mv "$S" solaar_$VERSION.orig.tar.gz

cd solaar-*
cp -a "$DEBIAN" .

ls -1 "$RULES_D"/*.rules | while read rule; do
	target=`basename "$rule"`
	target=${target#??-}
	target=${target%.rules}
	cp -av "$rule" ./debian/solaar.$target.udev
done

debuild "$@"
cd ..
cp -au ./solaar_*.changes "$DIST"
cp -au ./solaar_*.dsc "$DIST"
cp -au ./solaar_*.debian.tar.gz "$DIST"
cp -au ./solaar_*.orig.tar.gz "$DIST"
cp -au ./solaar_*.deb "$DIST"
