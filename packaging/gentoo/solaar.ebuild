#
# ebuild script by Carlos Silva
#

pkg_setup() {
    enewgroup plugdev

    CONFIG_CHECK="HID_LOGITECH_DJ"
    linux-info_pkg_setup

    python_pkg_setup
}

src_install() {
    distutils_src_install

    #insinto /usr/share
    #doins -r share/icons

    udev_dorules rules.d/*.rules

    dodoc README.md COPYING COPYRIGHT
    #if use doc; then
    #    dodoc -r docs/*
    #fi

    dobin ${FILESDIR}/solaar ${FILESDIR}/solaar-cli
}

pkg_postinst() {
    gnome2_icon_cache_update
    elog "To be able to use this application, the user must be on the plugdev group."
}

pkg_preinst() { gnome2_icon_savelist; }
pkg_postrm() { gnome2_icon_cache_update; }
