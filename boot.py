"""Terminal raster adaptation of _renderer.js displayLine/displayTitleScreen.

The upstream boot_log.txt is a prerecorded theatrical intro, not diagnostics
from the host running this port. No kernel/service changes occur here.
"""
import io
import math
from pathlib import Path
import select
import shutil
import sys
import termios
import time
import tty

from PIL import Image as Raster, ImageDraw
from protocol import Image
from render import BG, CYAN, DIM, font

ROOT=Path(__file__).parent


def line_delay(i,count):
    # Upstream displayLine switch order matters at its last two lines.
    if i in (2,4):return .5
    if 4<i<25:return .03
    if i==25:return .4
    if i==42:return .3
    if 42<i<82 or i==83:return .025
    if count-2<=i<count:return .3
    return (1-i/1000)**3*.025


def title_frame(width,height,t):
    """Original 400/200/100/300/100/500/1000ms title keyframes."""
    image=Raster.new('RGB',(width,height),BG)
    d=ImageDraw.Draw(image);vh=height/100
    grid=t>=.4 and not (.6<=t<1.6)
    if grid:
        step=max(2,round(2.04*vh))
        # Equivalent subtle intersection grid to main.css, not added circuits.
        for y in range(step//2,height,step):
            for x in range(step//2,width,step):d.point((x,y),fill='#262828')
    if t<.4:return image
    f=font(max(12,round(10*vh)));label='eDEX-UI'
    box=d.textbbox((0,0),label,font=f)
    tw,th=box[2]-box[0],box[3]-box[1]
    x=(width-tw)//2;y=(height-th)//2
    pad=max(2,round(2*vh));border=max(1,round(.46*vh))
    rect=(x-pad,y-pad,x+tw+pad,y+th+pad)
    if .7<=t<1:d.rectangle(rect,fill=CYAN)
    if 1<=t<1.1 or t>=1.6:d.rectangle(rect,outline=CYAN,width=border)
    if 1.1<=t<1.6:
        # Two clipped slices, alternating at the upstream 50ms glitch cadence.
        layer=Raster.new('RGB',(tw+2*pad,th+2*pad),BG)
        ImageDraw.Draw(layer).text((pad-box[0],pad-box[1]),label,font=f,fill=CYAN)
        cut=round(layer.height*.4);phase=int((t-1.1)/.05)%2
        image.paste(layer.crop((0,0,layer.width,cut)),(x-pad-round(tw*(.01 if phase else .05)),y-pad))
        image.paste(layer.crop((0,cut,layer.width,layer.height)),(x-pad+round(tw*(.01 if phase else .03)),y-pad+cut))
    else:
        opacity=min(1,(t-.4)/.3)
        ink=tuple(round(int(CYAN[i:i+2],16)*opacity) for i in (1,3,5))
        d.text((x-box[0],y-box[1]),label,font=f,fill=ink)
        if t<1.1:d.line((x-pad,y+th+pad,x+tw+pad,y+th+pad),fill=CYAN,width=border)
    return image


def play():
    cols,rows=shutil.get_terminal_size((180,50));cols-=1;rows-=1
    # Query actual pixel geometry without terminal request/reply races.
    # Linux TIOCGWINSZ reports ypixel/xpixel when Kitty supplies it.
    import fcntl,struct
    _,_,xp,yp=struct.unpack('HHHH',fcntl.ioctl(sys.stdout.fileno(),termios.TIOCGWINSZ,b'\0'*8))
    width=round((xp or (cols+1)*9)*cols/(cols+1))
    height=round((yp or (rows+1)*18)*rows/(rows+1))
    stream=sys.stdout.buffer;image=Image(stream);state=termios.tcgetattr(sys.stdin.fileno())
    tty.setcbreak(sys.stdin.fileno())
    stream.write(b'\x1b[?1049h\x1b[?25l');stream.flush()
    log=(ROOT/'assets/boot_log.txt').read_text().split('\n')
    times=[];at=0
    for i in range(1,len(log)+1):times.append(at);at+=line_delay(i,len(log))
    title_start=at+.3;started=time.monotonic();last_count=-1
    try:
        while True:
            tick=time.monotonic();elapsed=tick-started
            if select.select([sys.stdin],[],[],0)[0]:
                sys.stdin.buffer.read1(4096);break
            if elapsed>=title_start+2.6:break
            if elapsed<title_start:
                count=sum(v<=elapsed for v in times)
                if count==last_count:time.sleep(.01);continue
                last_count=count
                frame=Raster.new('RGB',(width,height),BG);d=ImageDraw.Draw(frame)
                size=max(9,round(height*.014));line_height=round(size*1.2)
                visible=log[:count][-max(1,(height-30)//line_height):]
                y=height-len(visible)*line_height
                for line in visible:d.text((0,y),line,font=font(size),fill=CYAN);y+=line_height
                d.text((8,4),'UPSTREAM INTRO / prerecorded boot sequence',font=font(10),fill=DIM)
            else:frame=title_frame(width,height,elapsed-title_start)
            output=io.BytesIO();frame.save(output,format='PNG',compress_level=2)
            image.pixels(output.getvalue(),update=image.loaded)
            if not image.loaded:raise RuntimeError('Image initialization failed')
            image.place(cols,rows)
            time.sleep(max(0,1/20-(time.monotonic()-tick)))
    finally:
        image.close();stream.write(b'\x1b[?25h\x1b[?1049l');stream.flush()
        termios.tcsetattr(sys.stdin.fileno(),termios.TCSADRAIN,state)
