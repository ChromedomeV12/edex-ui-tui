"""Clickable eDEX-style trapezoid tabs; actual shells live in tmux panes."""
import io
import os
import select
import shutil
import signal
import sys
import termios
import time
import tty
from PIL import Image as Raster,ImageDraw
from protocol import Image
from render import BG,FG,DIM,GRAY,font
from tmux_control import query


def tab_geometry(width,height,viewport_height=1080):
    """main_shell.css: normal 16px text + .7vh/.4vh padding; skewX(35deg).

    Keep the artwork shallow even when tmux rounds its pane to whole cells.
    """
    import math
    strip=min(height,max(20,round(19+viewport_height*.011)))
    return width/5,strip,math.tan(math.radians(35))*strip


def hit_tab(x,y,width,height,viewport_height=1080):
    step,strip,cut=tab_geometry(width,height,viewport_height)
    if not 0<=x<width or not 0<=y<strip:return None
    # CSS skewed separators lean right toward the bottom of the strip.
    return min(5,max(1,int((x+cut*(.5-y/strip))/step)+1))


def render_tabs(width,height,active,occupied,viewport_height=1080):
    from palette import blend
    image=Raster.new('RGB',(width,height),BG);d=ImageDraw.Draw(image)
    step,strip,cut=tab_geometry(width,height,viewport_height);face=font(16)
    for i in range(5):
        x=i*step;end=(i+1)*step
        polygon=[(x-cut/2,0),(end-cut/2,0),(end+cut/2,strip-1),(x+cut/2,strip-1)]
        selected=i+1==active
        d.polygon(polygon,fill=FG if selected else BG)
        if i:d.line((x-cut/2,0,x+cut/2,strip-1),fill=blend(.5))
        label=('MAIN SHELL' if i==0 else 'SHELL '+str(i+1)) if occupied[i] else 'EMPTY'
        d.text((x+step/2,strip/2),label,font=face,anchor='mm',fill=BG if selected else FG)
    # Clip at the viewport edges as the original overflow:hidden strip does.
    d.line((0,0,width-1,0),fill=blend(.5))
    d.line((0,strip-1,width-1,strip-1),fill=blend(.5))
    output=io.BytesIO();image.save(output,format='PNG');return output.getvalue()


def main():
    from keyboard import MOUSE
    from workspaces import switch
    from shell_edges import ShellFrame
    alive=True
    def stop(*_):
        nonlocal alive
        alive=False
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGHUP,stop)
    settings=termios.tcgetattr(sys.stdin.fileno());tty.setcbreak(sys.stdin.fileno())
    stream=sys.stdout.buffer;image=Image(stream);last=None;last_place=0;buffer=b'';bootstrap_at=None;png=None;raw=None;last_query=0
    frame=ShellFrame(stream)
    stream.write(b'\x1b[?1049h\x1b[?25l\x1b[?1000h\x1b[?1006h');stream.flush()
    try:
        while alive:
            if time.monotonic()-last_query>=.5:
                raw=query('display-message','-p','-t',os.environ['TMUX_PANE'],
                      '#{window_height}|#{window_active}|#{session_attached}|#{pane_width}|#{pane_height}|#{client_cell_width}|#{client_cell_height}|#{@edex-active-slot}|#{@edex-slot-1}|#{@edex-slot-2}|#{@edex-slot-3}|#{@edex-slot-4}|#{@edex-slot-5}|#{client_pid}|#{client_created}|#{@edex-shell-frame}|#{@edex-shell}|#{P:#{pane_id}/#{pane_left}/#{pane_top}/#{pane_width}/#{pane_height}~}|#{@edex-modal-open}|#{window_zoomed_flag}|#{@edex-shell-padding}|#{@edex-popup-box}|#{@edex-layout-revision}')
                last_query=time.monotonic()
            if raw is None:time.sleep(.2);continue
            fields=raw.split('|')
            if len(fields)!=23 or fields[1]=='0' or fields[2]=='0':
                last=None;time.sleep(.2);continue
            window_rows=int(fields[0]);cols,rows,cw,ch=map(int,fields[3:7]);cols=max(1,cols-1);cw=cw or 9;ch=ch or 20
            viewport_height=window_rows*ch
            active=int(fields[7] or '1');occupied=[bool(pane) for pane in fields[8:13]]
            state=(cols,rows,cw,ch,viewport_height,active,tuple(occupied),tuple(fields[13:15]),fields[22])
            if select.select([sys.stdin],[],[],.1)[0]:
                buffer+=os.read(sys.stdin.fileno(),1024)
                while match:=MOUSE.match(buffer):
                    if match[4]==b'M' and int(match[1])==0:
                        slot=hit_tab((int(match[2])-1)*cw,(int(match[3])-1)*ch,cols*cw,rows*ch,viewport_height)
                        if slot is not None:switch(slot);last_query=0
                    buffer=buffer[match.end():]
                if buffer and not b'\x1b[<'.startswith(buffer) and not buffer.startswith(b'\x1b[<'):buffer=b''
            parent_refreshed=False
            if state!=last:
                image.close();image=Image(stream);stream.write(b'\x1b[2J')
                png=render_tabs(cols*cw,rows*ch,active,occupied,viewport_height)
                image.pixels(png)
                image.place(cols,rows)
                parent_refreshed=True
                last=state;last_place=time.monotonic();bootstrap_at=time.monotonic()+.75
            if bootstrap_at is not None and time.monotonic()>=bootstrap_at:
                # A previous renderer may finish alternate-screen cleanup just
                # after respawn. Recover its cleared placeholder cells once.
                image.pixels(png,update=True);image.place(cols,rows)
                parent_refreshed=True;last_place=time.monotonic();bootstrap_at=None
            if time.monotonic()-last_place>=1:
                image.place(cols,rows,repaint=False);last_place=time.monotonic()
                parent_refreshed=True
            # Kitty resolves a virtual placement from the placeholder cells
            # tmux paints. Create its relative child after bootstrap repaint,
            # rather than referencing a parent that has not reached Kitty yet.
            if fields[15]=='1' and bootstrap_at is None:
                frame.update((image,fields[16],os.environ.get('TMUX_PANE')),fields[17],
                             cols,rows,cw,ch,viewport_height,
                             recover=parent_refreshed,hidden=fields[19]=='1',padding=fields[20],popup=fields[21])
    finally:
        frame.close()
        image.close();stream.write(b'\x1b[?1006l\x1b[?1000l\x1b[?25h\x1b[?1049l');stream.flush()
        termios.tcsetattr(sys.stdin.fileno(),termios.TCSADRAIN,settings)


if __name__=='__main__':main()
