#!/usr/bin/env python3
"""Isolated tmux session for the eDEX terminal port; no user config installation."""
import argparse
import os
from pathlib import Path
import shutil
import secrets
import shlex
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent

SOCKET=os.environ.get('EDEX_TMUX_SOCKET') or 'edex-terminal-'+str(os.getuid() if hasattr(os,'getuid') else 'test')


def binding_command(command):
    # Keep the selected socket in bound commands so server-launched children
    # (key bindings, workspace switching) resolve this server instead of the
    # per-uid default socket.
    if os.environ.get('EDEX_TMUX_SOCKET'):
        return 'EDEX_TMUX_SOCKET='+shlex.quote(SOCKET)+' '+command
    return command


def sync_server_env():
    # Keep the selected socket in the server's session environment so children
    # the server launches inherit it: key binding subprocesses, workspace
    # switching and keyboard management.
    if os.environ.get('EDEX_TMUX_SOCKET'):
        tmux('set-environment','-t','edex','EDEX_TMUX_SOCKET',SOCKET)
    if os.environ.get('EDEX_GRAPHICS_TRANSPORT'):
        tmux('set-environment','-t','edex','EDEX_GRAPHICS_TRANSPORT',os.environ['EDEX_GRAPHICS_TRANSPORT'])


def tmux(*args):
    return subprocess.run(['tmux','-L',SOCKET,'-f',str(ROOT/'tmux.conf'),*args],
                          check=True,capture_output=True,text=True).stdout.strip()


def configure_grid_surface(shell, session='edex', run=None):
    """Keep the grid outside opaque shells, scoped to this app's window."""
    if os.environ.get('EDEX_GRID_BACKGROUND') != '1':
        return
    run = run or tmux
    run('set-option', '-t', session, '@edex-grid-background', '1')
    run('set-environment', '-t', session, 'EDEX_GRID_BACKGROUND', '1')
    run('set-option', '-w', '-t', shell, 'window-style', 'bg=default,fg=#aacfd1')
    run('set-option', '-w', '-t', shell, 'window-active-style', 'bg=default,fg=#aacfd1')
    run('set-option', '-p', '-t', shell, 'window-style', 'bg=#05080d,fg=#aacfd1')


def toggle_keyboard():
    from workspaces import lock
    with lock():_toggle_keyboard()


def _toggle_keyboard():
    session='edex'
    sync_server_env()
    shell=tmux('show-options','-v','-t',session,'@edex-shell')
    files=tmux('show-options','-v','-t',session,'@edex-files')
    token=tmux('show-options','-p','-v','-t',shell,'@edex-input-token')
    tabs=tmux('show-options','-qv','-t',session,'@edex-tabs')
    tab_height=tmux('display-message','-p','-t',tabs,'#{pane_height}') if tabs else None
    panes=tmux('list-panes','-a','-F','#{pane_id} #{pane_title} #{window_name}')
    keyboard=next((line.split() for line in panes.splitlines()
                   if line.split()[1:2]==['Keyboard']),None)
    if keyboard and keyboard[2]!='_keyboard':
        tmux('break-pane','-d','-s',keyboard[0],'-n','_keyboard')
        height=int(tmux('display-message','-p','-t',files,'#{window_height}'))
        tmux('resize-pane','-t',files,'-y',str(max(1,int(height*.30))))
        tmux('select-pane','-t',shell)
    else:
        if keyboard:pane=keyboard[0]
        else:
            pane=tmux('new-window','-d','-t',session,'-n','_keyboard','-P','-F','#{pane_id}',
                      sys.executable,str(ROOT/'keyboard.py'),'--shell-pane',shell,'--token',token)
            tmux('select-pane','-t',pane,'-T','Keyboard')
        height=int(tmux('display-message','-p','-t',files,'#{window_height}'))
        tmux('resize-pane','-t',files,'-y',str(max(1,int(height*.36))))
        tmux('join-pane','-d','-s',pane,'-t',files,'-h','-l','62%')
        tmux('select-pane','-t',shell)
    # tmux can take rows from the tab strip when resizing the full-width bottom.
    if tabs:tmux('resize-pane','-t',tabs,'-y',tab_height)
    # Even a fast hide/show can clear placeholders without changing final size.
    tmux('set-option','-t',session,'@edex-layout-revision',str(time.monotonic_ns()))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--detach',action='store_true');p.add_argument('--stop',action='store_true')
    p.add_argument('--toggle-keyboard',action='store_true',help='Show/hide the touch keyboard in the existing session')
    p.add_argument('--install-switcher',action='store_true',help='Add the shell tab strip to the existing demo')
    p.add_argument('--install-shell-frame',action='store_true',help='Add experimental clipped shell edges to an existing session')
    p.add_argument('--files',choices=['auto','yazi','superfile','preview'],default='auto')
    p.add_argument('--skip-intro',action='store_true',help='Skip the upstream-derived theatrical startup sequence')
    p.add_argument('--fps',type=int,choices=(24,30,48,60),default=24,
                   help='Animation target for a new session; higher rates need local performance testing')
    p.add_argument('--graphics-transport',choices=['direct','tempfile'],
                   default=os.environ.get('EDEX_GRAPHICS_TRANSPORT','direct'),
                   help='Use tempfile only when Kitty and this process share a filesystem; direct for SSH')
    p.add_argument('--display-font',type=Path,help='Optional local font, e.g. a licensed United Sans Medium TTF/OTF')
    p.add_argument('--light-font',type=Path,help='Optional matching local light-weight face')
    p.add_argument('--cwd',default=os.getcwd());args=p.parse_args()
    os.environ['EDEX_GRAPHICS_TRANSPORT']=args.graphics_transport
    if not shutil.which('tmux'):p.error('Install tmux first')
    if args.stop:
        tmux('kill-session','-t','=edex');return
    if args.toggle_keyboard:
        toggle_keyboard();return
    if args.install_switcher:
        from workspaces import install
        install();return
    if args.install_shell_frame:
        from shell_edges import install
        install();return
    if os.environ.get('TMUX'):p.error('Launch from Kitty outside tmux; this uses its own tmux server')
    if not os.environ.get('KITTY_WINDOW_ID'):p.error('Launch in Kitty; tmux graphics support must be tested there')
    for option,var in [(args.display_font,'EDEX_DISPLAY_FONT'),(args.light_font,'EDEX_LIGHT_FONT')]:
        if option:
            from PIL import ImageFont
            try:ImageFont.truetype(str(option),16)
            except OSError:p.error(f'Cannot read font: {option}; supply a supported TTF/OTF file')
            os.environ[var]=str(option.resolve())
    existing=subprocess.run(['tmux','-L',SOCKET,'has-session','-t','=edex'],capture_output=True).returncode==0
    if not existing:
        cols,rows=shutil.get_terminal_size((180,55))
        if cols<140 or rows<40:p.error('Prototype layout needs at least 140 columns by 40 rows')
        if not args.skip_intro and not args.detach:
            from boot import play
            play()
        new_session_args=['-d','-s','edex','-c',str(Path(args.cwd).resolve()),
                          '-x',str(cols),'-y',str(rows),'-P','-F','#{pane_id}']
        if os.environ.get('EDEX_TMUX_SOCKET'):
            # Give the first shell the selected socket explicitly: on an
            # existing server the new session's environment comes from the
            # server, not from this client.
            new_session_args=['-e','EDEX_TMUX_SOCKET='+SOCKET,*new_session_args]
        shell=tmux('new-session',*new_session_args)
        tmux('select-pane','-t',shell,'-T','Shell')
        configure_grid_surface(shell)
        token=secrets.token_hex(24)
        tmux('set-option','-p','-t',shell,'@edex-input-token',token)
        tmux('set-option','-t','edex','@edex-shell',shell)
        sync_server_env()
        keyboard_cmd=binding_command(shlex.join([sys.executable,str(ROOT/'launch.py'),'--toggle-keyboard']))
        tmux('bind-key','K','run-shell',keyboard_cmd)
        def instrument(kind,target,orientation,percentage,before=False):
            cmd=['split-window','-d','-t',target,orientation,'-l',percentage,'-P','-F','#{pane_id}']
            if before:cmd.append('-b')
            cmd.extend([sys.executable,str(ROOT/'panel.py'),kind,'--shell-pane',shell,'--fps',str(args.fps)])
            pane=tmux(*cmd);tmux('select-pane','-t',pane,'-T',kind.capitalize());return pane
        try:
            # Upstream main_shell 65vw, side columns 17vw. Bottom row spans
            # the full window; an optional keyboard shares it with files.
            files=tmux('split-window','-d','-f','-v','-t',shell,'-l','30%',
                       '-c',str(Path(args.cwd).resolve()),'-P','-F','#{pane_id}',
                       sys.executable,str(ROOT/'navigator.py'),'--program',args.files,
                       '--shell-pane',shell)
            tmux('select-pane','-t',files,'-T','Files')
            tmux('set-option','-t','edex','@edex-files',files)
            instrument('system',shell,'-h','17%',True)
            instrument('network-column',shell,'-h','20%')
            from workspaces import install
            install()
            from popups import install as install_popups
            install_popups()
            tmux('select-pane','-t',shell)
        except Exception:
            tmux('kill-session','-t','edex');raise
    if existing:
        # Repair the session environment of a pre-existing session so children
        # the server spawns after attach inherit the selected socket.
        sync_server_env()
    if args.detach:
        print('Created isolated session. Attach: tmux -L '+SOCKET+' attach -t edex');return
    os.execvp('tmux',['tmux','-L',SOCKET,'attach-session','-t','edex'])


if __name__=='__main__':main()
