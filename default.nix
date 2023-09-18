{stdenv,
lib,
autoPatchelfHook,
python3
}:

stdenv.mkDerivation rec{
  pname = "solaar";
  version = "1.1.10rc3"; #builtins.readFile src+"/lib/solaar/version";

  src = ./.;

  outputs = [ "out" "udev" ];

  nativeBuiltInputs = [
    autoPatchelfHook
  ];

  builtInputs = [
    python3
  ];

  installPhase = ''
    install -m755 -D $src/bin/solaar $out/bin/solaar
    ln -s $out/bin/solaar $out/bin/solaar-cli

    install -m444 -D $src/rules.d-uinput/*.rules $udev/etc/udev/rules.d/

  '';
  postInstall = ''
    install -m444 -t $udev/etc/udev/rules.d rules.d-uinput/*.rules
  '';
}
