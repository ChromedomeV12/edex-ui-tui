"""On-demand eDEX keymap pane: SGR mouse input -> this session's shell only.

Layout/key commands adapted from the pinned upstream en-US.json (GPL-3.0).
Sticky modifiers accommodate single-touch terminals; no global key capture.
"""
import io
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import subprocess
import sys
import termios
import time
import tty

from functools import lru_cache
from PIL import Image as Raster, ImageDraw, ImageFont, ImageFilter
from protocol import Image
from render import BG, CYAN, DIM, FG, GRAY, font
from tmux_control import query

LAYOUT = json.loads((Path(__file__).parent/'assets/en-US.json').read_text())
CTRLSEQ = ['', '\x1b', '\x1c', '\x1d', '\x1e', '\x1f', '\x11', '\x17',
           '\x12', '\x12', '\x19', '\x15', '\x10', '\x01', '\x13', '\x04',
           '\x06', '\x1a', '\x18', '\x03', '\x16', '\x02']
MOUSE = re.compile(rb'\x1b\[<(\d+);(\d+);(\d+)([mM])')


def decode_command(value):
    return re.sub(r'~~~CTRLSEQ(\d+)~~~', lambda m: CTRLSEQ[int(m[1])], value)


GEOMETRY=json.loads((Path(__file__).parent/'assets/keyboard-geometry.json').read_text())
ARROWS=json.loads((Path(__file__).parent/'assets/keyboard-arrows.json').read_text())


def geometry_transform(width,height):
    # Uniform fitting preserves square keys and the original row stagger.
    base_width,base_height=GEOMETRY['canvas']
    scale=min(width/base_width,height/base_height)
    return scale,(width-base_width*scale)/2,(height-base_height*scale)/2


def key_geometry(width,height,state='normal'):
    scale,dx,dy=geometry_transform(width,height)
    measured_keys=[(key,entry) for keys,row in zip(LAYOUT.values(),GEOMETRY['states'][state])
                   for key,entry in zip(keys,row)]
    down=next(entry['rect'] for key,entry in measured_keys
              if key['name']=='ESCAPED|-- ICON: ARROW_DOWN')
    for keys,measured in zip(LAYOUT.values(),GEOMETRY['states'][state]):
        for key,entry in zip(keys,measured):
            x,y,w,h=entry['rect']
            if key['name'].startswith('ESCAPED|-- ICON: '):
                # Correct the source row offset and SVG padding together. Drawing
                # and mouse routing consume this same adapted geometry.
                if key['name'].endswith('ARROW_UP'):x=down[0]+(down[2]-w)/2
                _,_,iw,ih=entry['icon_rect']
                entry=dict(entry,rect=[x,y,w,h],
                           icon_rect=[x+(w-iw)/2,y+(h-ih)/2,iw,ih])
            yield (dx+x*scale,dy+y*scale,dx+(x+w)*scale,dy+(y+h)*scale,key,entry)


def key_boxes(width,height,state='normal'):
    return [box[:5] for box in key_geometry(width,height,state)]


@lru_cache(maxsize=48)
def key_font(size):
    if os.environ.get('EDEX_DISPLAY_FONT'):return font(size)
    return ImageFont.truetype(str(Path(__file__).parent/'assets/fonts/Rajdhani-SemiBold.ttf'),size)


@lru_cache(maxsize=48)
def arrow_stamp(direction,size,ink):
    # Reuse the existing librsvg renderer once per size/color, never per frame.
    svg=ARROWS[direction].replace('<svg ',f'<svg fill="{ink}" ')
    converter=shutil.which('rsvg-convert')
    if converter:
        png=subprocess.run([converter,'-w',str(size),'-h',str(size)],input=svg.encode(),
                           capture_output=True,check=True,timeout=3).stdout
        return Raster.open(io.BytesIO(png)).convert('RGBA')
    # Basic fallback when librsvg is absent; full fidelity needs that dependency.
    stamp=Raster.new('RGBA',(size,size));draw=ImageDraw.Draw(stamp)
    points=[(12,8),(17,13),(14,13),(14,17),(10,17),(10,13),(7,13)]
    turns={'UP':0,'RIGHT':1,'DOWN':2,'LEFT':3}[direction];rotated=[]
    for x,y in points:
        x-=12;y-=12
        for _ in range(turns):x,y=-y,x
        rotated.append(((x+12)*size/24,(y+12)*size/24))
    draw.rectangle((size*3/24,size*3/24,size*21/24,size*21/24),outline=ink)
    draw.polygon(rotated,fill=ink)
    return stamp


class Keyboard:
    def __init__(self):
        self.modifiers=set()

    def press(self,key):
        value=key['cmd']
        if value.startswith('ESCAPED|-- '):
            modifier=value.split(' ',1)[1].split(':')[0].strip('- ')
            if modifier in self.modifiers:self.modifiers.remove(modifier)
            else:self.modifiers.add(modifier)
            return b''
        prefix=''
        for modifier,field in [('FN','fn_cmd'),('CTRL','ctrl_cmd'),('ALT','alt_cmd')]:
            if modifier in self.modifiers and field in key:
                prefix=modifier;value=key[field];break
        if not prefix and 'SHIFT' in self.modifiers:
            value=key.get('shift_cmd',value.upper() if len(value)==1 else value)
        if not prefix and 'CAPSLCK' in self.modifiers and len(value)==1 and value.isalpha():
            value=value.swapcase()
        if 'CTRL' in self.modifiers and prefix!='CTRL' and len(value)==1 and '@'<=value.upper()<='_':
            value=chr(ord(value.upper())&31)
        if 'ALT' in self.modifiers and prefix!='ALT':value='\x1b'+value
        self.modifiers.intersection_update({'CAPSLCK','FN'})
        return decode_command(value).encode()

    def png(self,width,height,pressed=None,reveal=None):
        # Supersampling preserves the CSS's fractional borders and rounded joins.
        from background import surface
        aa=2;image=surface((width*aa,height*aa),BG);d=ImageDraw.Draw(image)
        state='fn' if 'FN' in self.modifiers else 'shift' if 'SHIFT' in self.modifiers else 'normal'
        boxes=list(key_geometry(width,height,state));scale,dx,dy=geometry_transform(width,height)
        edge=tuple(round((a+b)/2) for a,b in zip(bytes.fromhex(FG[1:]),bytes.fromhex(BG[1:])))
        enter_mask=Raster.new('L',image.size);enter_draw=ImageDraw.Draw(enter_mask)
        enter_active=pressed is not None and pressed['cmd']=='\r'
        for x0,y0,x1,y1,key,entry in boxes:
            if key['cmd']=='\r':enter_draw.rounded_rectangle(tuple(v*aa for v in (x0,y0,x1,y1)),radius=4.968*scale*aa,fill=255)
        if enter_active:image.paste(CYAN,mask=enter_mask)
        for x0,y0,x1,y1,key,entry in boxes:
            active=any(key['cmd'].startswith('ESCAPED|-- '+m+':') for m in self.modifiers)
            active=active or key is pressed or (pressed is not None and key['cmd']==pressed['cmd']=='\r')
            box=tuple(v*aa for v in (x0,y0,x1,y1));radius=4.968*scale*aa
            if key['cmd']=='\r':
                enter_draw.rounded_rectangle(box,radius=radius,fill=255)
                enter_active=enter_active or active
            elif active:d.rounded_rectangle(box,radius=radius,fill=CYAN)
            elif key['cmd']==' ':
                d.rounded_rectangle(box,radius=radius,outline=edge,width=max(1,round(2.052*scale*aa)))
            if key['name'].startswith('ESCAPED|-- ICON: '):
                # SVG occupies calc(100% - 1vh), with the source's .5vh offset.
                x,y,w,h=entry['icon_rect']
                side=max(1,round(min(w,h)*scale*aa))
                stamp=arrow_stamp(key['name'].split('_')[-1],side,BG if active else FG)
                image.paste(stamp,(round((dx+x*scale)*aa),round((dy+y*scale)*aa)),stamp)
                continue
            for label in entry['labels']:
                x,y,w,h=label['rect'];face=key_font(max(8,round(label['font']*scale*aa)))
                ascent,descent=face.getmetrics()
                baseline=(dy+y*scale)*aa+(h*scale*aa-ascent-descent)/2+ascent
                d.text(((dx+(x+w/2)*scale)*aa,baseline),label['text'],anchor='ms',font=face,fill=BG if active else FG)
        # The original two Enter elements overlap; their union is the clickable
        # L shape, including the lower stem extending into the next row's gap.
        border=max(1,round(2.052*scale*aa))
        inner=enter_mask.filter(ImageFilter.MinFilter(border*2+1))
        if not enter_active:
            from PIL import ImageChops
            image.paste(edge,mask=ImageChops.subtract(enter_mask,inner))
        # Preserve the source's reveal staggering without periodic texture resets.
        if reveal is not None:
            for row,delay in enumerate([.3,.2,0,.25,.2]):
                progress=max(0,min(1,(reveal-delay)/(.6 if row==4 else .7)))
                extent=width*(1-(1-progress)**3)/2
                y0=round(row*height/5)*aa;y1=round((row+1)*height/5)*aa
                if extent<width/2:
                    blank=(0,0,0,0) if image.mode=='RGBA' else BG
                    d.rectangle((0,y0,max(0,round(width/2-extent))*aa,y1),fill=blank)
                    d.rectangle((min(width,round(width/2+extent))*aa,y0,width*aa,y1),fill=blank)
        image=image.resize((width,height),Raster.Resampling.LANCZOS)
        out=io.BytesIO();image.save(out,format='PNG',compress_level=2);return out.getvalue()


def send_to_shell(pane,token,payload):
    # Verify a random marker on the exact shell pane before every injection.
    # A stale pane ID or another session cannot become the keyboard's target.
    if not payload:return
    check=subprocess.run(['tmux','show-options','-p','-v','-t',pane,'@edex-input-token'],
                         capture_output=True,text=True,timeout=2)
    if check.returncode or check.stdout.strip()!=token:
        raise RuntimeError('Keyboard target shell is no longer available')
    subprocess.run(['tmux','send-keys','-t',pane,'-H',*[f'{b:02x}' for b in payload]],
                   check=True,timeout=2)


def route_key(args,payload):
    # A popup owns focus. The optional keyboard must not type behind it.
    modal=query('show-options','-qv','-t','edex','@edex-modal-open')
    if modal is None or modal=='1':return
    active=query('show-options','-qv','-t','edex','@edex-shell')
    if active:send_to_shell(active,args.token,payload)


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--shell-pane',required=True);p.add_argument('--token',required=True)
    args=p.parse_args();alive=True
    def stop(*_):
        nonlocal alive
        alive=False
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    signal.signal(signal.SIGHUP,stop)
    stream=sys.stdout.buffer;settings=termios.tcgetattr(sys.stdin.fileno())
    tty.setcbreak(sys.stdin.fileno());keyboard=Keyboard();image=Image(stream)
    stream.write(b'\x1b[?1049h\x1b[?25l\x1b[?1000h\x1b[?1006h');stream.flush()
    buffer=b'';size=None;pressed=None;press_until=0;client_signature=None;was_visible=False;shown_at=0;state=None;last_query=0;last_clients=0
    revision=None;bootstrap_at=None;last_place=0;revealed=False
    try:
        while alive:
            now=time.monotonic()
            # Hidden-window panes are kept alive but do no raster work.
            if now-last_query>=.5:
                state=query('display-message','-p','-t',os.environ['TMUX_PANE'],
                        '#{window_active},#{session_attached},#{pane_width},#{pane_height},#{client_cell_width},#{client_cell_height},#{@edex-layout-revision}')
                last_query=now
            if state is None:time.sleep(.1);continue
            values=state.split(',')
            if len(values)!=7 or values[0]=='0' or values[1]=='0':
                was_visible=False;time.sleep(.2);continue
            _,_,cols,rows,cw,ch=map(int,values[:6])
            new_revision=values[6]
            if not was_visible:shown_at=now;revealed=False
            cols=max(1,cols-1);rows=max(1,rows-1);cw=cw or 8;ch=ch or 16
            width,height=cols*cw,rows*ch
            if min(width,height)<40:time.sleep(.2);continue
            dirty=False
            if select.select([sys.stdin],[],[],.05)[0]:
                buffer+=os.read(sys.stdin.fileno(),4096)
                while buffer:
                    match=MOUSE.match(buffer)
                    if match:
                        button,x,y=int(match[1]),int(match[2]),int(match[3])
                        if match[4]==b'M' and button==0:
                            px,py=(x-.5)*cw,(y-.5)*ch
                            for x0,y0,x1,y1,key in key_boxes(width,height,'fn' if 'FN' in keyboard.modifiers else 'shift' if 'SHIFT' in keyboard.modifiers else 'normal'):
                                if x0<=px<x1 and y0<=py<y1:
                                    route_key(args,keyboard.press(key))
                                    pressed=key;press_until=now+.12;dirty=True;break
                        buffer=buffer[match.end():];continue
                    if buffer in (b'\x1b',b'\x1b[') or (buffer.startswith(b'\x1b[<') and len(buffer)<64):break
                    # Physical input in this pane also goes only to the marked shell.
                    if buffer.startswith(b'\x1b[<'):buffer=b'';break
                    end=buffer.find(b'\x1b[<',1)
                    payload=buffer if end<0 else buffer[:end]
                    route_key(args,payload)
                    buffer=b'' if end<0 else buffer[end:]
            newsize=(cols,rows,cw,ch)
            if pressed is not None and now>=press_until:pressed=None;dirty=True
            signature=client_signature
            if now-last_clients>=1:
                reply=query('list-clients','-F','#{client_name},#{client_pid},#{client_created}')
                if reply is not None:signature=reply
                last_clients=now
            redraw=newsize!=size or not was_visible or signature!=client_signature or new_revision!=revision
            # A slow first PNG can outlast the reveal window. Always submit
            # its final visible frame rather than leaving the initial blank.
            if dirty or redraw or not revealed:
                if redraw:image.close();image=Image(stream);stream.write(b'\x1b[2J')
                image.pixels(keyboard.png(width,height,pressed,reveal=now-shown_at),update=image.loaded and not redraw)
                if redraw:
                    image.placement_id=3-image.placement_id;image.place(cols,rows)
                    last_place=now;bootstrap_at=now+.75
                stream.flush();size=newsize
                if now-shown_at>=1.05:revealed=True
            # A join/resize can clear placeholder cells after the first paint.
            # Repair once after tmux settles; steady heartbeats only place metadata.
            if bootstrap_at is not None and now>=bootstrap_at:
                image.place(cols,rows);stream.flush();last_place=now;bootstrap_at=None
            elif bootstrap_at is None and now-last_place>=2:
                image.place(cols,rows,repaint=False);stream.flush();last_place=now
            was_visible=True;client_signature=signature;revision=new_revision
    finally:
        image.close();stream.write(b'\x1b[?1006l\x1b[?1000l\x1b[?25h\x1b[?1049l');stream.flush()
        termios.tcsetattr(sys.stdin.fileno(),termios.TCSADRAIN,settings)


if __name__=='__main__':main()
