{
  description = "Solaar is Open Source Logitech Driver for Linux";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-22.11";
  };

  outputs = { self, nixpkgs }: {

    packages.x86_64-linux.default = (
      import nixpkgs {
        currentSystem = "x86_64-linux";
        localSystem = "x86_64-linux";
      }).pkgs.callPackage ./default.nix {};
  };
}
