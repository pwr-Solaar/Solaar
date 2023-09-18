{ stdenv
, lib
, python3Packages
, python3
, dbus
, dbus-glib
, pkg-config

, gobject-introspection
, gtk3
, wrapGAppsHook
, gdk-pixbuf
, libappindicator
, librsvg
}:

let
  dbus-python = ps: with ps; [
    (
      buildPythonPackage rec {
        pname = "dbus-python";
        version = "1.3.2";

        format = "other";
        outputs = [ "out" "dev" ];

        src = fetchPypi {
          inherit pname version;
          sha256 = "sha256-rWeBkwhhi1BpU3viN/jmjKHH/Mle5KEh/mhFsUGCSPg=";
        };
        doCheck = false;
        nativeBuildInputs = [ pkg-config ];
        buildInputs = [ dbus dbus-glib ];
        propagatedBuildInputs = [];

        nativeCheckInputs = [ dbus.out pygobject3 ];

        postInstall = ''
          cp -r dbus_python.egg-info $out/${python.sitePackages}/
        '';
      }
    )
  ];
in
python3Packages.buildPythonApplication rec{
  pname = "solaar";
  version = builtins.readFile "${src}/lib/solaar/version";

  src = ./.;

  outputs = [ "out" "udev" ];

  nativeBuildInputs = [
    gdk-pixbuf
    gobject-introspection
    wrapGAppsHook
  ];

  buildInputs = [
    libappindicator
    librsvg
  ];

  propagatedBuildInputs = with python3Packages; [
    evdev
    gtk3
    psutil
    pygobject3
    pyudev
    pyyaml
    xlib
    (python3.withPackages dbus-python)
  ];

  # the -cli symlink is just to maintain compabilility with older versions where
  # there was a difference between the GUI and CLI versions.
  postInstall = ''
    ln -s $out/bin/solaar $out/bin/solaar-cli

    install -Dm444 -t $udev/etc/udev/rules.d rules.d-uinput/*.rules
  '';

  dontWrapGApps = true;

  preFixup = ''
    makeWrapperArgs+=("''${gappsWrapperArgs[@]}")
  '';

  # no tests
  doCheck = false;

  pythonImportsCheck = [ "solaar" ];

}
