"""Raster adaptations of the pinned eDEX globe, CPU charts and memory grid.

GPL-3.0. Original eDEX-UI by GitSquared; ENCOM globe by Rob Scanlon.
World polygons are taken from the selected security-patched upstream's grid.json.
"""
from collections import deque
import io
import json
import math
from pathlib import Path
import random
import os
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
# Exact selected upstream tron.json surface and primary ink. This project
# reconstructs eDEX; it does not replace the collection's other TRON palettes.
BG = '#05080d'; FG = '#c4e4e6'; BLUE = '#aacfd1'; CYAN = '#aacfd1'
DIM = '#426067'; GRAY = '#9dbabe'; ORANGE = '#aacfd1'
TILES = json.loads((ROOT/'assets/grid.json').read_text())['tiles']
MESH = [[(p['x']/500,p['y']/500,p['z']/500) for p in tile['b']] for tile in TILES]
ORDER = list(range(440)); random.Random(12).shuffle(ORDER)


@lru_cache(maxsize=16)
def font(size, weight='medium'):
    local=os.environ.get('EDEX_LIGHT_FONT' if weight=='light' else 'EDEX_DISPLAY_FONT','')
    for name in [local, str(ROOT/'assets/fonts'/('Rajdhani-Light.ttf' if weight=='light' else 'Rajdhani-Medium.ttf')), 'DejaVuSansMono.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
                 '/usr/share/fonts/TTF/DejaVuSansMono.ttf', 'C:/Windows/Fonts/consola.ttf']:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def render(kind, width, height, data, elapsed, directory=None):
    image = Image.new('RGB', (width, height), BG)
    d = ImageDraw.Draw(image); scale = max(0.65, min(1, width/350))
    f = font(round(17*scale)); small = font(round(13*scale), 'light')
    def text(y, value, color=FG, x=12):
        d.text((x, y), str(value), font=f, fill=color)
    def header(label, sub=''):
        d.line((10, 34, width-10, 34), fill=DIM)
        text(10, label, CYAN)
        if sub: text(height-24, sub, GRAY)
    def graph(values, box, color, maximum=100):
        x0,y0,x1,y1=box
        for fraction in [0,.5,1]:
            y=y1-(y1-y0)*fraction;d.line((x0,y,x1,y),fill=DIM)
        valid=[(x0+i*(x1-x0)/79,y1-(y1-y0)*min(1,v/maximum))
               for i,v in enumerate(values) if v is not None]
        if len(valid)>1:d.line(valid,fill=color,width=2)
    if kind=='globe':
        header('WORLD VIEW', 'Geographic mesh / no endpoint geolocation')
        # Upstream globe's 45-second day and 0.630-radian camera view angle.
        angle=elapsed*2*math.pi/45; tilt=.630
        ca,sa,ct,st=math.cos(angle),math.sin(angle),math.cos(tilt),math.sin(tilt)
        radius=min(width*.43,(height-85)*.45);cx=width/2;cy=height/2+6
        polygons=[]
        for tile in MESH:
            points=[];depth=0
            for x,y,z in tile:
                x,z=x*ca+z*sa,-x*sa+z*ca
                y,z=y*ct-z*st,y*st+z*ct
                depth+=z;points.append((cx+x*radius,cy-y*radius))
            depth/=len(points)
            if depth>0:
                polygons.append((depth,points))
        for depth,points in sorted(polygons):
            c=tuple(int(v*(.35+.65*depth)) for v in (111,195,223))
            d.polygon(points,fill=BG,outline=c)
        d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),outline=DIM)
    elif kind=='memory':
        mem=data['memory'];total=mem['MemTotal'];active=mem.get('Active',total-mem['MemAvailable'])
        available=max(0,mem['MemAvailable']-mem['MemFree'])
        used=min(440,round(440*active/total));cached=min(440-used,round(440*available/total))
        header('MEMORY', '440 cells / active, reclaimable, free')
        text(48,f'{active/2**30:.1f} / {total/2**30:.1f} GiB active',BLUE)
        colors=[DIM]*440
        for i in ORDER[:used]:colors[i]=CYAN
        for i in ORDER[used:used+cached]:colors[i]=BLUE
        cellx=(width-24)/40;celly=min(14,(height-145)/11)
        for i,color in enumerate(colors):
            col,row=divmod(i,11);x=12+col*cellx;y=85+row*celly
            d.rectangle((x,y,x+max(1,cellx-2),y+max(1,celly-3)),fill=color)
        swap=mem.get('SwapTotal',0);usedswap=swap-mem.get('SwapFree',0)
        text(height-66,f'SWAP   {usedswap/2**30:.1f} / {swap/2**30:.1f} GiB',GRAY)
    elif kind=='cpu':
        cpus=data['cpus'];valid=[v for v in cpus if v is not None]
        header('CPU USAGE', f'{len(cpus)} logical CPUs / sampled locally')
        text(48,f'Average {sum(valid)/len(valid):.1f}%' if valid else 'Sampling...',BLUE)
        groups=[list(range(0,max(1,len(cpus)//2))),list(range(max(1,len(cpus)//2),len(cpus)))]
        for number,indices in enumerate(groups):
            top=90+number*max(70,(height-155)/2);bottom=top+max(40,(height-185)/2)
            for core in indices:
                graph([row[core] if core<len(row) else None for row in data['history']],
                      (12,top,width-12,bottom),BLUE if core%2 else CYAN)
    elif kind=='network':
        header('NETWORK I/O','Non-loopback interface totals / local host')
        for i,label in enumerate(['RECEIVE','TRANSMIT']):
            rate=data['network'][i]
            text(50+i*28,f'{label}  {rate/1024:.1f} KiB/s' if rate is not None else label+'  sampling',BLUE if i==0 else ORANGE)
            values=[row[i] for row in data['net_history']]
            maximum=max(1024,max((v for v in values if v is not None),default=0))
            top=120+i*max(55,(height-180)/2)
            graph(values,(12,top,width-12,top+max(35,(height-210)/2)),CYAN if i==0 else ORANGE,maximum)
    elif kind=='files':
        header('FILES', 'Shell working directory / read-only listing')
        text(48,str(directory),BLUE)
        try:
            entries=sorted(Path(directory).iterdir(),key=lambda p:(not p.is_dir(),p.name.casefold()))
            columns=max(1,width//220);rows=max(1,(height-100)//24)
            for index,p in enumerate(entries[:columns*rows]):
                col,row=divmod(index,rows)
                name=''.join(c if c.isprintable() else '?' for c in p.name)
                text(80+row*24,('/ ' if p.is_dir() else '  ')+name[:25],CYAN if p.is_dir() else FG,12+col*(width//columns))
        except OSError as e:text(80,type(e).__name__,ORANGE)
    out=io.BytesIO();image.save(out,format='PNG',compress_level=2)
    return out.getvalue()
