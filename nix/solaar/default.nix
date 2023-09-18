{stdenv,
lib,
builtins,
python3
}:

stdenv.mkDerivation rec{
  pname = "solaar";
  version = builtins.readFile "../../lib/solaar/version";

  src = "../../";

  builtInputs = [
    python3
  ];

  installPhase = ''
    cp ${src}/bin/solaar ${out}/bin/solaar
    ln -s ${out}/bin/solaar ${out}/bin/solaar-cli

    cp -r ${src}/lib ${out}/lib
  '';
}
