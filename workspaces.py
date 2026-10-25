"""Five eDEX shell slots backed by ordinary tmux shell panes."""
import argparse
import contextlib
import fcntl
import hashlib
import os
from pathlib import Path
import shlex
import sys
from launch import tmux,ROOT,SOCKET,binding_command,sync_server_env


@contextlib.contextmanager
def lock():
    # One lock per tmux server: different sockets own separate session state,
    # and the hash keeps the filename safe for any EDEX_TMUX_SOCKET value.
    digest=hashlib.sha256(SOCKET.encode()).hexdigest()[:16]
    path=Path(os.environ.get('XDG_RUNTIME_DIR','/tmp'))/f'edex-terminal-{os.getuid()}-{digest}.workspaces.lock'
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        if os.fstat(fd).st_uid!=os.getuid():raise PermissionError('Workspace lock owner mismatch')
        fcntl.flock(fd,fcntl.LOCK_EX);yield
    finally:os.close(fd)


def option(name):
    return tmux('show-options','-qv','-t','edex',name)


def install():
    with lock():
        sync_server_env()
        if option('@edex-tabs'):return
        shell=option('@edex-shell')
        tmux('set-option','-t','edex','@edex-slot-1',shell)
        tmux('set-option','-p','-t',shell,'remain-on-exit','on')
        tmux('set-option','-t','edex','@edex-active-slot','1')
        pane=tmux('split-window','-d','-b','-v','-t',shell,'-l','2','-P','-F','#{pane_id}',
                  sys.executable,str(ROOT/'shell_tabs.py'))
        tmux('set-option','-t','edex','@edex-tabs',pane)
        tmux('select-pane','-t',pane,'-T','Shell tabs')
        for slot in range(1,6):
            command=binding_command(shlex.join([sys.executable,str(ROOT/'workspaces.py'),str(slot)]))
            tmux('bind-key',str(slot),'run-shell',command)
        tmux('select-pane','-t',shell)


def switch(slot):
    if slot not in range(1,6):raise ValueError('Shell slot must be 1–5')
    with lock():
        current=option('@edex-shell');target=option('@edex-slot-'+str(slot))
        if not target:
            cwd=tmux('display-message','-p','-t',current,'#{pane_current_path}')
            target=tmux('new-window','-d','-t','edex','-n','_shell'+str(slot),'-c',cwd,'-P','-F','#{pane_id}')
            token=tmux('show-options','-p','-v','-t',current,'@edex-input-token')
            tmux('set-option','-p','-t',target,'@edex-input-token',token)
            tmux('set-option','-p','-t',target,'remain-on-exit','on')
            tmux('set-option','-t','edex','@edex-slot-'+str(slot),target)
            if option('@edex-grid-background') == '1':
                tmux('set-option','-p','-t',target,'window-style','bg=#05080d,fg=#aacfd1')
        if tmux('display-message','-p','-t',target,'#{pane_dead}')=='1':
            tmux('respawn-pane','-t',target)
        if target==current:return
        tmux('swap-pane','-d','-s',target,'-t',current)
        tmux('set-option','-t','edex','@edex-shell',target)
        tmux('set-option','-t','edex','@edex-active-slot',str(slot))
        tmux('select-pane','-t',target)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('slot',type=int,choices=range(1,6));args=parser.parse_args();switch(args.slot)
