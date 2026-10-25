"""On-demand native process details, scoped to this project's tmux server."""
import fcntl
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

from launch import ROOT, SOCKET, tmux, binding_command


def open_processes():
    # Hold one controller until the popup closes; repeated clicks do no work.
    digest=hashlib.sha256(SOCKET.encode()).hexdigest()[:16]
    path=Path(os.environ.get('XDG_RUNTIME_DIR','/tmp'))/f'edex-{os.getuid()}-{digest}.popup.lock'
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        if os.fstat(fd).st_uid!=os.getuid():raise PermissionError('Popup lock owner mismatch')
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        tmux('has-session','-t','=edex')
        shell=tmux('show-options','-qv','-t','edex','@edex-shell')
        if not shell:raise RuntimeError('No project shell')
        cwd=tmux('display-message','-p','-t',shell,'#{pane_current_path}')
        cols,rows=map(int,tmux('display-message','-p','-t',shell,'#{window_width}/#{window_height}').split('/'))
        width,height=min(cols,max(20,int(cols*.8))),min(rows,max(10,int(rows*.75)))
        left,top=(cols-width)//2,(rows-height)//2
        box=f'{left}/{top}/{width}/{height}'
        tmux('set-option','-t','edex','@edex-frame-popup-ready','')
        tmux('set-option','-t','edex','@edex-popup-box',box)
        tmux('set-option','-t','edex','@edex-modal-open','1')
        try:
            if tmux('show-options','-qv','-t','edex','@edex-shell-frame')=='1':
                deadline=time.monotonic()+1.5
                while time.monotonic()<deadline:
                    if tmux('show-options','-qv','-t','edex','@edex-frame-popup-ready')==box:break
                    time.sleep(.05)
            # display-popup waits for its child. Escape/C-c or viewer quit
            # closes the popup and releases the on-screen input guard.
            try:
                tmux('display-popup','-E','-t',shell,'-x','C','-y','C','-w',str(width),'-h',str(height),
                     '-d',cwd,'-T','Active Processes | q / Escape: close | P: CPU | M: memory',
                     '-s','fg=#aacfd1,bg=#05080d','-S','fg=#aacfd1,bg=#05080d',
                     shlex.join([sys.executable,str(ROOT/'popups.py'),'--viewer']))
            except subprocess.CalledProcessError as error:
                if error.returncode not in (129,130,143):raise
        finally:
            tmux('set-option','-t','edex','@edex-popup-box','')
            tmux('set-option','-t','edex','@edex-modal-open','0')
    finally:os.close(fd)


def install():
    command=binding_command(shlex.join([sys.executable,str(ROOT/'popups.py')]))
    tmux('bind-key','P','run-shell','-b',command)


if __name__=='__main__':
    if sys.argv[1:]==['--viewer']:
        viewer=shutil.which('top')
        if not viewer:raise SystemExit('Install procps (top) for process details')
        # Use an existing viewer, with native sorting, scrolling and quit.
        os.execv(viewer,[viewer,'-o','%CPU'])
    elif not sys.argv[1:]:open_processes()
    else:raise SystemExit('Usage: popups.py [--viewer]')
