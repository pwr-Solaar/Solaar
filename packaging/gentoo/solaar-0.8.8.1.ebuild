# Copyright 1999-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI=5

PYTHON_COMPAT=( python{2_7,3_2} )

inherit distutils-r1 udev user linux-info gnome2-utils

DESCRIPTION="Solaar is a Linux device manager for Logitech's Unifying Receiver peripherals"
HOMEPAGE="http://pwr-solaar.github.io/Solaar/"
SRC_URI="https://github.com/pwr/Solaar/archive/${PV}.tar.gz"

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~amd64"
IUSE="doc"

RDEPEND="${PYTHON_DEPS}
		 dev-python/pyudev
		 dev-python/pygobject[${PYTHON_USEDEP}]"

MY_P="Solaar-${PV}"
S="${WORKDIR}/${MY_P}"

DOCS=( README.md COPYING COPYRIGHT ChangeLog )

pkg_setup() {
	enewgroup plugdev

	CONFIG_CHECK="HID_LOGITECH_DJ"
	linux-info_pkg_setup
}

src_install() {
	distutils-r1_src_install

	udev_dorules rules.d/*.rules

	if use doc; then
		dodoc -r docs/*
	fi
}

pkg_postinst() {
	gnome2_icon_cache_update
	elog "To be able to use this application, the user must be on the plugdev group."
}

pkg_preinst() { gnome2_icon_savelist; }
pkg_postrm() { gnome2_icon_cache_update; }

