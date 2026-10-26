#!/usr/bin/env python3
"""Open a local window, or run inside the current Kitty terminal over SSH."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
CONTROLS = {'-h', '--help', '--stop', '--toggle-keyboard',
            '--install-switcher', '--install-shell-frame'}


def command(args):
    args = list(args)
    env = dict(os.environ)
    explicit_inline = '--in-place' in args
    inline = explicit_inline or bool(env.get('SSH_CONNECTION') or env.get('SSH_TTY'))
    args = [arg for arg in args if arg != '--in-place']
    if inline:
        # Keep direct-transfer clients separate from a local tempfile session.
        uid = str(os.getuid() if hasattr(os, 'getuid') else 'test')
        if not env.get('EDEX_TMUX_SOCKET'):
            env['EDEX_TMUX_SOCKET'] = 'edex-terminal-' + uid + '-direct'
    launch = [sys.executable, str(ROOT / 'launch.py')]
    if CONTROLS.intersection(args):
        return [*launch, *args], env
    if inline:
        if env.get('TERM') != 'xterm-kitty' and not explicit_inline:
            raise ValueError('Graphics client not recognized. If your terminal supports Kitty '
                             'placeholders and animation frames, use --in-place. '
                             'Mosh graphics are not supported.')
        for index, arg in enumerate(args):
            if ((arg == '--graphics-transport' and args[index + 1:index + 2] != ['direct']) or
                    (arg.startswith('--graphics-transport=') and arg != '--graphics-transport=direct')):
                raise ValueError('In-place graphics require direct transfer, not host-local temporary files.')
        env['EDEX_IN_PLACE'] = '1'
        env['EDEX_GRAPHICS_TRANSPORT'] = 'direct'
        env.pop('EDEX_GRID_BACKGROUND', None)
        return [*launch, '--graphics-transport', 'direct', *args], env
    env['EDEX_GRID_BACKGROUND'] = '1'
    # The new Kitty owns a new PTY; do not carry the invoking tmux identity.
    env.pop('TMUX', None)
    env.pop('TMUX_PANE', None)
    return ['kitty', '--class', 'edex-ui-tui', '--config', str(ROOT / 'kitty-grid.conf'),
            '-o', 'background_image=' + str(ROOT / 'assets/background-grid-1080.png'),
            *launch, '--graphics-transport', 'tempfile', *args], env


def main():
    try:
        if '--help' in sys.argv[1:] or '-h' in sys.argv[1:]:
            print('Entry point: local launch opens a dedicated Kitty window.\n'
                  'SSH uses the current terminal with direct graphics.\n'
                  '--in-place: use the current Kitty-graphics-compatible terminal explicitly.\n'
                  'Requires Unicode placeholders and animation frames; Mosh is unsupported.\n', flush=True)
        argv, env = command(sys.argv[1:])
        if env.get('EDEX_IN_PLACE') == '1' and not CONTROLS.intersection(sys.argv[1:]):
            if not (sys.stdin.isatty() and sys.stdout.isatty()):
                raise ValueError('In-place launch needs an interactive terminal; use ssh -t.')
        os.execvpe(argv[0], argv, env)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
    except FileNotFoundError:
        print(f'Cannot start {argv[0]}; install the runtime dependencies.', file=sys.stderr)
        raise SystemExit(127)


if __name__ == '__main__':
    main()
