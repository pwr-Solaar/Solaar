---
title: Uninstalling Solaar
layout: page
---

# Uninstalling Solaar

## Uninstalling from Debian systems

If you installed Solaar using `apt`, you can remove it by running:

```bash
sudo apt remove --purge solaar
```

## Uninstalling from GitHub

If you cloned and installed Solaar from GitHub manually, navigate to the cloned directory and run:

```bash
sudo make uninstall
```

## Removing Configuration Files

Solaar may leave behind configuration files in your home directory. To delete them, run:

```bash
rm -rf ~/.config/solaar
```

## Verifying Uninstallation

To confirm that Solaar is fully removed, try running:

```bash
which solaar
```

If no output is returned, Solaar has been successfully uninstalled.
