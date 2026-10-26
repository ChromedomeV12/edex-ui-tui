"""Stage the runtime and notices under DESTDIR; never edit user configuration."""
import argparse
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
MODULES = ('app', 'background', 'boot', 'border_frame', 'columns', 'file_icons',
           'keyboard', 'launch', 'layout', 'metrics', 'navigator', 'palette',
           'panel', 'popups', 'protocol', 'render', 'shell_edges', 'shell_tabs',
           'tmux_control', 'workspaces')
DATA = ('kitty.conf', 'kitty-grid.conf', 'tmux.conf', 'LICENSE', 'NOTICE.md', 'UPSTREAM.json')
SUFFIXES = {'.json', '.css', '.js', '.ttf', '.txt', '.png', '.lua', '.toml', '.md'}


def runtime_files():
    files = [ROOT / (name + '.py') for name in MODULES] + [ROOT / name for name in DATA]
    for directory in ('assets', 'references', 'navigation'):
        files.extend(path for path in sorted((ROOT / directory).rglob('*'))
                     if path.is_file() and (path.suffix in SUFFIXES or path.name == 'LICENSE')
                     and '__pycache__' not in path.parts)
    for path in files:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Expected a regular bundled file: {path.relative_to(ROOT)}')
    return files


def stage(destdir, package_name='edex-ui-tui', interpreter='/usr/bin/python'):
    if not re.fullmatch(r'[a-z0-9][a-z0-9@._+-]*', package_name):
        raise ValueError('package name must be a single Arch package name')
    if interpreter not in ('/usr/bin/python', '/usr/bin/python3'):
        raise ValueError('unsupported package interpreter')
    destdir = Path(destdir)
    app = destdir / 'usr/share/edex-ui-tui'
    for source in runtime_files():
        target = app / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o644)
    binary = destdir / 'usr/bin/edex-ui-tui'
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text(f'#!/bin/sh\nexec {interpreter} /usr/share/edex-ui-tui/app.py "$@"\n',
                      encoding='utf-8', newline='\n')
    binary.chmod(0o755)
    desktop = destdir / 'usr/share/applications/edex-ui-tui.desktop'
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text('[Desktop Entry]\nType=Application\nName=eDEX-UI TUI\n'
                       'Comment=Terminal workspace with system and network instruments\n'
                       'Exec=edex-ui-tui\nIcon=utilities-terminal\nTerminal=false\n'
                       'Categories=System;TerminalEmulator;\n', encoding='utf-8', newline='\n')
    docs = destdir / 'usr/share/doc/edex-ui-tui'
    docs.mkdir(parents=True, exist_ok=True)
    for source in [ROOT / name for name in ('README.md', 'CONTRIBUTING.md', 'SECURITY.md')] + sorted((ROOT / 'docs').glob('*.md')):
        target = docs / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    licenses = destdir / 'usr/share/licenses' / package_name
    licenses.mkdir(parents=True, exist_ok=True)
    for name, source in [('LICENSE', ROOT / 'LICENSE'), ('NOTICE.md', ROOT / 'NOTICE.md'),
                         ('OFL.txt', ROOT / 'assets/fonts/OFL.txt')]:
        shutil.copyfile(source, licenses / name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destdir', type=Path, required=True)
    parser.add_argument('--package-name', default='edex-ui-tui')
    parser.add_argument('--interpreter', choices=('/usr/bin/python', '/usr/bin/python3'), default='/usr/bin/python')
    args = parser.parse_args()
    stage(args.destdir, args.package_name, args.interpreter)
