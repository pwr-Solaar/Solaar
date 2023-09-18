{stdenv,
lib,
autoPatchelfHook,
python3Packages
}:

stdenv.mkDerivation rec{
  pname = "solaar";
  version = "1.1.10rc3"; #builtins.readFile src+"/lib/solaar/version";

  src = ./.;

  outputs = [ "out" "udev" ];

  nativeBuiltInputs = [
    autoPatchelfHook
  ];

  propagatedBuiltInputs = with python3Packages; [
    evdev
  ];

  installPhase = ''
    install -m755 -D $src/bin/solaar $out/bin/solaar
    ln -s $out/bin/solaar $out/bin/solaar-cli

    mkdir -p $udev/etc/udev/rules.d

    install -m444 -t $udev/etc/udev/rules.d $src/rules.d-uinput/*.rules
  '';
}
