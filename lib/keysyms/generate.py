#!/usr/bin/env python3
"""Extract key symbol encodings from X11 header files."""

from pathlib import Path
from pprint import pprint
from re import findall
from subprocess import run
from tempfile import TemporaryDirectory

repo = "https://gitlab.freedesktop.org/xorg/proto/xorgproto.git"
pattern = r"#define XK_(\w+)\s+0x(\w+)(?:\s+/\*\s+U\+(\w+))?"
xf86pattern = r"#define XF86XK_(\w+)\s+0x(\w+)(?:\s+/\*\s+U\+(\w+))?"


def main():
    keysymdef = {}
    keysym_files = [
        ("include/X11/keysymdef.h", pattern, ""),
        ("include/X11/XF86keysym.h", xf86pattern, "XF86_"),
    ]

    with TemporaryDirectory() as temp:
        run(["git", "clone", repo, "."], cwd=temp)

        for filename, extraction_pattern, prefix in keysym_files:
            text = Path(temp, filename).read_text()
            for name, sym, _ in findall(extraction_pattern, text):
                sym = int(sym, 16)
                if keysymdef.get(f"{prefix}{name}", None):
                    print(f"KEY DUP {prefix}{name}")
                keysymdef[f"{prefix}{name}"] = sym

    with open("keysymdef.py", "w") as f:
        f.write("# flake8: noqa\nkey_symbols = \\\n")
        pprint(keysymdef, f)


if __name__ == "__main__":
    main()
