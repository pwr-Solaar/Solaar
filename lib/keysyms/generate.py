#!/usr/bin/env python3
from pathlib import Path
from pprint import pprint
from re import findall
from subprocess import run
from tempfile import TemporaryDirectory

repo = 'https://github.com/freedesktop/xorg-proto-x11proto.git'
pattern = r'#define XK_(\w+)\s+0x(\w+)(?:\s+/\*\s+U\+(\w+))?'
xf86pattern = r'#define XF86XK_(\w+)\s+0x(\w+)(?:\s+/\*\s+U\+(\w+))?'


def main():
    keysymdef = {}

    with TemporaryDirectory() as temp:
        run(['git', 'clone', repo, '.'], cwd=temp)
        text = Path(temp, 'keysymdef.h').read_text()
        for name, sym, uni in findall(pattern, text):
            sym = int(sym, 16)
            uni = int(uni, 16) if uni else None
            if keysymdef.get(name, None):
                print('KEY DUP', name)
            keysymdef[name] = sym
        text = Path(temp, 'XF86keysym.h').read_text()
        for name, sym, uni in findall(xf86pattern, text):
            sym = int(sym, 16)
            uni = int(uni, 16) if uni else None
            if keysymdef.get('XF86_' + name, None):
                print('KEY DUP', 'XF86_' + name)
            keysymdef['XF86_' + name] = sym

    with open('keysymdef.py', 'w') as f:
        f.write('# flake8: noqa\nkeysymdef = \\\n')
        pprint(keysymdef, f)


if __name__ == '__main__':
    main()
