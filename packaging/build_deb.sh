#!/bin/sh

set -e

if test "$DEBSIGN_KEYID"; then
	test "$DEBEMAIL"
	test "$DEBFULLNAME"
else
	export DEBFULLNAME="$(/usr/bin/getent passwd "$USER" | \
				/usr/bin/cut --delimiter=: --fields=5 | /usr/bin/cut --delimiter=, --fields=1)"
	export DEBEMAIL="${EMAIL:-$USER@$(/bin/hostname --long)}"
fi
export DEBMAIL="$DEBEMAIL"

export DEBCHANGE_VENDOR=${DEBCHANGE_VENDOR:-$(/usr/bin/dpkg-vendor --query vendor | /usr/bin/tr 'A-Z' 'a-z')}
DISTRIBUTION=${DISTRIBUTION:-UNRELEASED}

cd "$(dirname "$0")/.."
DEBIAN_FILES="$PWD/packaging/debian"
DEBIAN_FILES_VENDOR="$PWD/packaging/$DEBCHANGE_VENDOR"
DIST_TARGET="$PWD/dist/$DEBCHANGE_VENDOR"

#
# build a python sdist package, then unpack and create .orig and source dir
#

VERSION="$(python2.7 setup.py --version)"
FULLNAME="$(python2.7 setup.py --fullname)"

export TMPDIR="${TMPDIR:-/tmp}/debbuild-$FULLNAME-$USER"
BUILD_DIR="$TMPDIR/$DEBCHANGE_VENDOR-$DISTRIBUTION"
/bin/rm --force --recursive "$BUILD_DIR"
/bin/mkdir --parents --mode=0700 "$BUILD_DIR"
python2.7 setup.py sdist --dist-dir="$BUILD_DIR" --formats=gztar --quiet

ORIG_FILE="$BUILD_DIR/solaar_$VERSION.orig.tar.gz"
/bin/mv "$BUILD_DIR/$FULLNAME.tar.gz" "$ORIG_FILE"
/bin/tar --extract --gunzip --file "$ORIG_FILE" --directory "$BUILD_DIR"

cd "$BUILD_DIR/$FULLNAME"
unset BUILD_DIR VERSION FULLNAME ORIG_FILE

#
# preparing to build the package
#

/bin/cp --archive --target-directory=. "$DEBIAN_FILES"

if test "$DEBSIGN_KEYID"; then
	BUILDER_MAIL="$(echo "$DEBEMAIL" | /bin/sed --expression='s/+[a-z]*@/@/')"
	MAINT_MAIL="$(/bin/grep '^Maintainer: ' debian/control | /usr/bin/cut --delimiter=' ' --fields=2)"
	echo "maintainer $MAINT_MAIL, builder $BUILDER_MAIL"
	# test "$MAINT_MAIL" = "$BUILDER_MAIL" &&
	# 	/bin/sed --in-place --expression="s/^Maintainer: .*$/Maintainer: $DEBFULLNAME <$DEBEMAIL>/" debian/control
else
	/bin/sed --in-place --file=- debian/control <<-CONTROL
		/^Maintainer:/ a\
		Changed-By: $DEBFULLNAME <$DEBEMAIL>
		CONTROL
fi

/usr/bin/debchange \
	--vendor "$DEBCHANGE_VENDOR" \
	--distribution "$DISTRIBUTION" \
	--force-save-on-release \
	--auto-nmu \
	$@

if test "$DEBCHANGE_VENDOR" = debian; then
	# if this is the main (Debian) build, update the source changelog
	/bin/cp --archive --no-target-directory debian/changelog "$DEBIAN_FILES"/changelog
else
	# else copy any additional files
	/bin/cp --archive --target-directory=debian/ "$DEBIAN_FILES_VENDOR"/* || true
fi

if test "$DEBSIGN_KEYID"; then
	# only build a source package, and sign it
	DPKG_BUILPACKAGE_OPTS="-sa -S -k$DEBSIGN_KEYID"
else
	# build an unsigned binary package
	DPKG_BUILPACKAGE_OPTS="-b -us -uc"
fi
/usr/bin/debuild \
	--lintian --tgz-check \
	--preserve-envvar=DISPLAY \
	$DPKG_BUILPACKAGE_OPTS \
	--lintian-opts --profile "$DEBCHANGE_VENDOR"

#
# place the resulting files in $DIST_TARGET
#

/bin/mkdir --parents "$DIST_TARGET"
/bin/cp --archive --backup=numbered --target-directory="$DIST_TARGET" ../solaar_$VERSION*
/bin/cp --archive --backup=numbered --target-directory="$DIST_TARGET" ../solaar-*_$VERSION* || true
