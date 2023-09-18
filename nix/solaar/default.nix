{stdenv,
lib,
autoPatchelfHook,
python3
}:

stdenv.mkDerivation rec{
  pname = "solaar";
  version = builtins.readFile "./lib/solaar/version";

  src = ./.;

  outputs = [ "out" "udev" ];

  nativeBuiltInputs = [
    autoPatchelfHook
  ];

  builtInputs = [
    python3
  ];

  installPhase = ''
    install -m755 -D bin/solaar $out/bin/solaar
    ln -s $out/bin/solaar $out/bin/solaar-cli
  '';
}
