{stdenv,
lib,
python3
}:

let
  src_path = "../../";
in
stdenv.mkDerivation rec{
  pname = "solaar";
  version = builtins.readFile src+"/lib/solaar/version";

  src = src_path;

  outputs = [ "out" "udev" ];

  builtInputs = [
    python3
  ];

  installPhase = ''
    install -m755 -D bin/solaar $out/bin/solaar
    ln -s $out/bin/solaar $out/bin/solaar-cli
  '';
}
