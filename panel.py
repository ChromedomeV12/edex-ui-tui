#!/usr/bin/env python3
"""One tmux instrument pane. GPL-3.0; see UPSTREAM.json for port provenance."""
import argparse
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import sys
import termios
import time
import tty
import zlib
from collections import deque

from metrics import Metrics
from protocol import Image
from render import render
from tmux_control import query


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('kind',choices=['cpu','memory','globe','network','files','system','network-column'])
    parser.add_argument('--shell-pane')
    parser.add_argument('--fps',type=int,default=24)
    args=parser.parse_args()
    if not sys.stdout.isatty():parser.error('A Kitty terminal pane is required')
    if not Path('/proc/stat').exists():parser.error('Linux / WSL is required')
    alive=True;resized=True
    def stop(*_):
        nonlocal alive
        alive=False
    def resize(*_):
        nonlocal resized
        resized=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    signal.signal(signal.SIGHUP,stop)
    signal.signal(signal.SIGWINCH,resize)
    stream=sys.stdout.buffer;image=Image(stream)
    metrics=Metrics();data=metrics.sample();last_sample=time.monotonic()
    started=last_sample;directory=Path.cwd();size=None
    attached=False;last_attach_check=0
    settings=termios.tcgetattr(sys.stdin.fileno());tty.setcbreak(sys.stdin.fileno())
    stream.write(b'\x1b[?1049h\x1b[?25l');stream.flush()
    if args.kind=='system':stream.write(b'\x1b[?1000h\x1b[?1006h');stream.flush()
    frames=0;total_bytes=0
    cell=(8,16)
    client_signature=None
    frame_times=deque(maxlen=2048);upload_times=deque(maxlen=2048);sample_times=deque(maxlen=256)
    next_frame=time.monotonic()
    last_report=0
    last_placement=0
    def report():
        if not os.environ.get('EDEX_METRIC_LOG'):return
        import json,statistics
        def summary(values):
            if not values:return {}
            ordered=sorted(values)
            return dict(median_ms=round(statistics.median(values)*1000,2),
                        p95_ms=round(ordered[min(len(values)-1,int(len(values)*.95))]*1000,2))
        Path(os.environ['EDEX_METRIC_LOG']).write_text(json.dumps(dict(
            frames=frames,png_bytes=total_bytes,seconds=time.monotonic()-started,
            raster=summary(frame_times),upload=summary(upload_times),sample=summary(sample_times))))
    try:
        while alive:
            tick=time.monotonic()
            if os.environ.get('TMUX') and tick-last_attach_check>=.5:
                result=query('display-message','-p','-t',os.environ['TMUX_PANE'],
                             '#{session_attached},#{window_active},#{window_zoomed_flag},#{pane_active}')
                last_attach_check=tick
                if result is None:
                    # Leave the existing image untouched. Don't mistake a
                    # delayed query for detach/resize or kill the instrument.
                    time.sleep(.1);continue
                try:
                    clients,active,zoomed,selected=map(int,result.split(','))
                    current=clients>0 and active and (not zoomed or selected)
                except ValueError:current=False
                if current:
                    signature=query('list-clients','-F','#{client_name},#{client_pid},#{client_created}')
                    if signature is not None:
                        if client_signature is not None and signature!=client_signature:resized=True
                        client_signature=signature
                if current and not attached:resized=True
                attached=current;last_attach_check=tick
            if os.environ.get('TMUX') and not attached:
                time.sleep(.1);continue
            if select.select([sys.stdin],[],[],0)[0]:
                incoming=os.read(sys.stdin.fileno(),1024)
                if incoming in (b'q',b'\x03',b'\x1b'):break
                if args.kind=='system':
                    from keyboard import MOUSE
                    match=MOUSE.match(incoming)
                    if match and match[1]==b'0' and match[4]==b'M':
                        _,pane_rows=shutil.get_terminal_size((40,20))
                        if (int(match[3])-1)/max(1,pane_rows-1)>=.78:
                            subprocess.Popen([sys.executable,str(Path(__file__).parent/'popups.py')],
                                             stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                                             stderr=subprocess.DEVNULL)
            if tick-last_sample>=1:
                sample_start=time.monotonic()
                data=metrics.sample();last_sample=tick
                sample_times.append(time.monotonic()-sample_start)
                if args.kind=='files' and args.shell_pane:
                    result=query('display-message','-p','-t',args.shell_pane,'#{pane_current_path}')
                    if result is not None:directory=Path(result)
            columns,rows=shutil.get_terminal_size((40,20));newsize=(columns,rows)
            if min(columns,rows)<4:
                time.sleep(.2);continue
            # One cell margin prevents bottom-right autowrap/scroll side effects.
            cols=min(250,columns-1);lines=min(250,rows-1)
            if (resized or size!=newsize) and os.environ.get('TMUX'):
                result=query('display-message','-p','#{client_cell_width},#{client_cell_height}')
                try:
                    cw,ch=map(int,(result or '').split(','))
                    if 0<cw<100 and 0<ch<200:cell=(cw,ch)
                except ValueError:pass
            width=max(180,cols*cell[0]);height=max(140,lines*cell[1])
            render_start=time.monotonic()
            if args.kind in ('system','network-column'):
                from columns import render_column
                raster=render_column(args.kind,width,height,data,tick-started,raster=True)
                png=zlib.compress(raster.tobytes(),1);frame_size=raster.size
            else:
                png=render(args.kind,width,height,data,tick-started,directory);frame_size=None
            frame_times.append(time.monotonic()-render_start)
            redraw=resized or size!=newsize
            if redraw:
                # Root animation frames have a fixed canvas size. On resize or
                # visibility restoration, retire this image and create a new
                # pane-local root rather than blending into the old canvas.
                image.close();image=Image(stream);stream.write(b'\x1b[2J')
            # Editing the root frame preserves the texture and placement.
            # Full image replacement every two seconds caused visible flashes.
            # Rebuild only for actual resize/visibility/client changes.
            upload_start=time.monotonic()
            image.pixels(png,update=image.loaded and not redraw,size=frame_size,
                         channels=len(raster.getbands()) if frame_size else 3)
            if redraw or tick-last_placement>=1:
                # Keep the placement ID and cells stable during animation.
                # Heartbeats repair only placement metadata; repaint cells on
                # actual resize/visibility recovery, never once per second.
                image.place(cols,lines,repaint=redraw)
                last_placement=tick
            if redraw:
                size=newsize;resized=False
            stream.flush();frames+=1;total_bytes+=len(png)
            upload_times.append(time.monotonic()-upload_start)
            if tick-last_report>=5:
                report();last_report=tick
            fps=max(1,min(args.fps,30)) if args.kind in ('globe','system','network-column') else 1
            next_frame+=1/fps
            now=time.monotonic()
            if next_frame<now:next_frame=now  # Drop late slots; never burst to catch up.
            time.sleep(max(0,next_frame-now))
    finally:
        if args.kind=='system':stream.write(b'\x1b[?1006l\x1b[?1000l')
        image.close();stream.write(b'\x1b[0m\x1b[?25h\x1b[?1049l');stream.flush()
        termios.tcsetattr(sys.stdin.fileno(),termios.TCSADRAIN,settings)
        # Developer-supplied lab log only; nothing enters source control.
        report()


if __name__=='__main__':main()
