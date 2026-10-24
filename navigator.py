"""Run an existing native navigator, without touching the user's configuration."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import signal
import time

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--program',choices=['auto','yazi','superfile','preview'],default='auto')
    p.add_argument('--shell-pane',required=True)
    args=p.parse_args()
    choices=['yazi','superfile'] if args.program=='auto' else [args.program]
    for name in choices:
        command=shutil.which('spf' if name=='superfile' else name)
        if command:
            if os.environ.get('TMUX_PANE'):
                # File navigation uses terminal text only. Yazi probes Kitty
                # through passthrough otherwise; replies go to tmux's focused
                # pane, potentially the shell. Disable only THIS pane's bypass.
                subprocess.run(['tmux','set-option','-p','-t',os.environ['TMUX_PANE'],
                                'allow-passthrough','off'],check=True)
            if name=='yazi':
                # No preview subprocess can emit competing multipart graphics.
                # Navigation/action bindings remain native Yazi.
                os.environ['YAZI_CONFIG_HOME']=str(ROOT/'navigation/yazi')
                if shutil.which('rsvg-convert') and os.environ.get('TMUX'):
                    from file_icons import Icons
                    icons=Icons();icons.prepare();os.environ.update(icons.environment())
                    child=subprocess.Popen([command,str(Path.cwd())])
                    def stop(signum,_):
                        if child.poll() is None:child.send_signal(signum)
                    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
                    try:
                        while child.poll() is None:
                            icons.refresh();time.sleep(.5)
                    finally:
                        if child.poll() is None:child.terminate();child.wait(timeout=3)
                    raise SystemExit(child.returncode)
            os.execv(command,[command,str(Path.cwd())])
    if args.program not in ('auto','preview'):
        p.error(f'{args.program} is not installed; choose --files auto or install it first')
    os.execv(sys.executable,[sys.executable,str(ROOT/'panel.py'),'files',
                            '--shell-pane',args.shell_pane])


if __name__=='__main__':main()
