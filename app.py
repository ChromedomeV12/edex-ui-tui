#!/usr/bin/env python3
"""Open the local eDEX window, or route a control to its selected session."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
CONTROLS = {'-h', '--help', '--stop', '--toggle-keyboard',
            '--install-switcher', '--install-shell-frame'}


def command(args):
    launch = [sys.executable, str(ROOT / 'launch.py')]
    if CONTROLS.intersection(args):
        return [*launch, *args], dict(os.environ)
    env = dict(os.environ, EDEX_GRID_BACKGROUND='1')
    # The new Kitty owns a new PTY; do not carry the invoking tmux identity.
    env.pop('TMUX', None)
    env.pop('TMUX_PANE', None)
    return ['kitty', '--class', 'edex-ui-tui', '--config', str(ROOT / 'kitty-grid.conf'),
            '-o', 'background_image=' + str(ROOT / 'assets/background-grid-1080.png'),
            *launch, '--graphics-transport', 'tempfile', *args], env


def main():
    argv, env = command(sys.argv[1:])
    try:
        os.execvpe(argv[0], argv, env)
    except FileNotFoundError:
        print(f'Cannot start {argv[0]}; install the runtime dependencies.', file=sys.stderr)
        raise SystemExit(127)


if __name__ == '__main__':
    main()
