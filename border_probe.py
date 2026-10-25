#!/usr/bin/env python3
"""Standalone clipped-shell frame probe: one native shell plus the border frame renderer.

From a desktop Kitty window outside tmux, on a dedicated named socket:

    EDEX_TMUX_SOCKET=edex-borders python3 border_probe.py --detach
    tmux -L edex-borders attach -t edex-border-probe
    EDEX_TMUX_SOCKET=edex-borders python3 border_probe.py --stop

Layout, session edex-border-probe, single window filling the Kitty window
(pane order top-to-bottom, left-to-right):
  header   full width, 2 rows, top-left; runs
           `border_frame.py --shell-pane <shell>`; the frame anchor; title
           Border; recorded in @edex-border-renderer
  left     2 cols; empty-command pane, no process
  shell    middle; the native shell with its own cursor, input, mouse and
           selection; title Shell; recorded in @edex-shell
  right    2 cols; empty-command pane
  bottom   full width, 2 rows; empty-command pane

Invariants: a named, non-default EDEX_TMUX_SOCKET is mandatory (launch.py's
edex-terminal-<uid> fallback is refused); a socket already hosting an
unrelated `edex` session is refused; --stop kills only this probe's marked
session (@edex-border-probe) and refuses unmarked or foreign sessions; a
failed launch kills only the immutable session id its own new-session
reported, so a launcher losing a race cannot kill a sibling's session; native
pane border glyphs are hidden per window (pane-border-format '', flat
#05080d styles), never in global or owner configuration; one attached client
is the supported limit; if the native shell exits, run --stop and relaunch.

Frame agent (border_frame.py): the header pane is the window's first pane, so
its first cell is the window top-left (relative anchor H=0, V=0; frame sized
to window_cols x window_rows). Gutter sizes are fixed here: 2 rows
top/bottom, 2 cols left/right; strokes belong only in those bands and the
corner cells. Pass the shell pane's live pixel bounds to render_frame as the
exclusive transparent shell_box. tmux reallocates natively on resize and
keeps the header first, so the anchor stays top-left; on zoom or detach the
anchor pane hides and the frame must hide with it.
"""
import argparse
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SESSION='edex-border-probe'
MARKER='@edex-border-probe'
SHELL_ID='@edex-shell'
RENDERER_ID='@edex-border-renderer'
SHELL_TITLE='Shell'
HEADER_TITLE='Border'
HEADER_ROWS='2'
GUTTER_ROWS='2'
GUTTER_COLS='2'
MIN_COLS=60
MIN_ROWS=20
SOCKET=''


def fail(message):
    print(f'border_probe: {message}',file=sys.stderr)
    sys.exit(1)


def tmux(*args):
    # The -f file applies only when this client starts the server; a running
    # server keeps the configuration it started with. That is why the border
    # glyph hiding is applied per window below instead of in global config.
    return subprocess.run(['tmux','-L',SOCKET,'-f',str(ROOT/'tmux.conf'),*args],
                          check=True,capture_output=True,text=True).stdout.strip()


def tmux_quiet(*args):
    # Best-effort probes against the socket; a missing server is not an error.
    r=subprocess.run(['tmux','-L',SOCKET,*args],capture_output=True,text=True)
    return r


def session_names():
    # Exact names from list-sessions: tmux target strings prefix-match, and a
    # bare `-t edex` would otherwise also hit `edex-border-probe`.
    r=tmux_quiet('list-sessions','-F','#{session_name}')
    return r.stdout.splitlines() if r.returncode==0 else []


def session_exists(name):
    return name in session_names()


def session_option(session,option):
    r=tmux_quiet('show-options','-v','-t',session,option)
    return r.stdout.strip() if r.returncode==0 else ''


def preflight(launch=True):
    global SOCKET
    SOCKET=os.environ.get('EDEX_TMUX_SOCKET') or ''
    if not SOCKET:
        fail('Set EDEX_TMUX_SOCKET to a named, non-default socket; this probe has no uid fallback, unlike launch.py')
    # Reject the exact default launch.py would pick, not merely empty values:
    # the probe must never share the baseline server.
    if SOCKET=='edex-terminal-'+str(os.getuid() if hasattr(os,'getuid') else 'test'):
        fail(f'{SOCKET} is the default launch.py socket; choose a distinct named socket for this probe')
    if not shutil.which('tmux'):
        fail('Install tmux first')
    if not launch:
        return
    if os.environ.get('TMUX'):
        fail('Launch from Kitty outside tmux; the probe uses its own tmux server')
    if not os.environ.get('KITTY_WINDOW_ID'):
        fail('Launch in Kitty; tmux graphics support must be tested there')
    if not (ROOT/'border_frame.py').is_file():
        fail('border_frame.py is missing from this tree; the renderer ships with this probe')


def renderer_command(shell):
    return [sys.executable,str(ROOT/'border_frame.py'),'--shell-pane',shell]


def hide_window_border_glyphs(window):
    # Per-window only: the native border lines between panes lose their format
    # text and flatten to the project background, so the frame's gutters are
    # the only visible boundary. Global and owner configuration untouched.
    tmux('set-option','-w','-t',window,'pane-border-format','')
    tmux('set-option','-w','-t',window,'pane-border-status','off')
    tmux('set-option','-w','-t',window,'pane-border-style','fg=#05080d,bg=#05080d')
    tmux('set-option','-w','-t',window,'pane-active-border-style','fg=#05080d,bg=#05080d')


def split_gutter(target,orientation,before=False):
    # An empty shell command leaves a process-free pane (pane_pid=0,
    # pane_dead=1 on tmux 3.4): the gutter reserves cells without a process.
    # Without -b the new pane lands below (-v) or right (-h) of the target;
    # with -b it lands above or left.
    cmd=['split-window','-d','-t',target,orientation,'-l',
         GUTTER_ROWS if orientation=='-v' else GUTTER_COLS,'-P','-F','#{pane_id}']
    if before:
        cmd.append('-b')
    cmd.append('')
    pane=tmux(*cmd)
    side='bottom' if orientation=='-v' else 'left' if before else 'right'
    tmux('set-option','-p','-t',pane,'@edex-border-side',side)


def new_session(cwd):
    # new-session reports the immutable session id ($N) alongside the shell
    # pane id. That id is the only ownership token: a failed launch may kill
    # only a session id this invocation's own new-session reported, never the
    # name, so a launcher losing a race cannot kill a sibling's session.
    cols,rows=shutil.get_terminal_size((180,55))
    if cols<MIN_COLS or rows<MIN_ROWS:
        fail(f'Probe window needs at least {MIN_COLS} columns by {MIN_ROWS} rows (got {cols} by {rows})')
    args=['-d','-s',SESSION,'-c',cwd,'-x',str(cols),'-y',str(rows),'-P','-F','#{session_id} #{pane_id}']
    # On an existing server a new session inherits the server environment, not
    # this client's: pass the socket selector explicitly, as launch.py does.
    args=['-e','EDEX_TMUX_SOCKET='+SOCKET,*args]
    session_id,shell=tmux('new-session',*args).split()
    return session_id,shell


def build(session_id,shell):
    tmux('select-pane','-t',shell,'-T',SHELL_TITLE)
    tmux('set-option','-t',session_id,MARKER,secrets.token_hex(16))
    # Session-scoped, never global: children the server later spawns in this
    # session inherit the selected socket.
    tmux('set-environment','-t',session_id,'EDEX_TMUX_SOCKET',SOCKET)
    # Window order: header, left, shell, right, bottom.
    header=tmux('split-window','-d','-v','-b','-t',shell,'-l',HEADER_ROWS,
                '-e','EDEX_TMUX_SOCKET='+SOCKET,'-P','-F','#{pane_id}',
                *renderer_command(shell))
    tmux('select-pane','-t',header,'-T',HEADER_TITLE)
    tmux('set-option','-p','-t',header,'@edex-border-side','top')
    split_gutter(shell,'-v')             # bottom gutter
    split_gutter(shell,'-h',before=True) # left gutter
    split_gutter(shell,'-h')             # right gutter
    window=tmux('display-message','-p','-t',shell,'#{window_id}')
    hide_window_border_glyphs(window)
    tmux('set-option','-t',session_id,SHELL_ID,shell)
    tmux('set-option','-t',session_id,RENDERER_ID,header)
    tmux('select-pane','-t',shell)


def stop():
    if not session_exists(SESSION):
        fail(f'No probe session {SESSION} on socket {SOCKET}; nothing to stop')
    session_id=tmux('display-message','-p','-t',SESSION,'#{session_id}')
    if not session_option(session_id,MARKER):
        fail(f'Session {SESSION} on socket {SOCKET} is not a marked probe session; refusing to stop it')
    tmux('kill-session','-t',session_id)
    print(f'Stopped probe session {SESSION} on socket {SOCKET}')


def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--cwd',default=os.getcwd(),help='Starting directory for the native shell')
    p.add_argument('--detach',action='store_true',help='Create and leave detached; print the attach command')
    p.add_argument('--stop',action='store_true',help='Stop only this probe\'s marked session on the selected socket')
    args=p.parse_args()
    preflight(launch=not args.stop)
    if args.stop:
        stop()
        return
    if session_exists('edex'):
        fail(f'Socket {SOCKET} already hosts an unrelated edex session; point EDEX_TMUX_SOCKET at a dedicated experiment socket')
    if session_exists(SESSION):
        if not session_option(SESSION,MARKER):
            fail(f'Session {SESSION} on socket {SOCKET} is not a marked probe session; refusing to reuse it (stop it first or use another socket)')
        # Marked probe session: reuse read-only and attach; the renderer keeps
        # the frame current across resize and reattach, so nothing is rebuilt.
    else:
        cwd=str(Path(args.cwd).resolve())
        session_id=''
        try:
            session_id,shell=new_session(cwd)
            build(session_id,shell)
        except subprocess.CalledProcessError as e:
            if session_id:
                tmux_quiet('kill-session','-t',session_id)
            detail=(e.stderr or e.stdout or '').strip()
            fail(f'Launch failed: tmux {" ".join(e.cmd[2:])}: {detail or e}')
        except Exception as e:
            if session_id:
                tmux_quiet('kill-session','-t',session_id)
            fail(f'Launch failed: {e}')
    if args.detach:
        print(f'Probe session {SESSION} ready on socket {SOCKET}. Attach: tmux -L {SOCKET} attach -t {SESSION}')
        return
    os.execvp('tmux',['tmux','-L',SOCKET,'attach-session','-t',SESSION])


if __name__=='__main__':main()
