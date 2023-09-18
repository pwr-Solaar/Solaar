{
  description = "Solaar is Open Source Logitech Driver for Linux";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-22.11";

    flake-compat = {
      url = "github:edolstra/flake-compat";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, flake-compat }: {

    packages.x86_64-linux.default = (
      import nixpkgs {
        currentSystem = "x86_64-linux";
        localSystem = "x86_64-linux";
      }).pkgs.callPackage ./nix/solaar/default.nix {};
  };
}
