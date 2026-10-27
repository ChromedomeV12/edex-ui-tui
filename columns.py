"""eDEX's two original mod_column sections, rasterized in separate tmux panes.

Module ordering/labels/geometry follow the pinned CSS and class DOM. Missing
telemetry is shown as --, never replaced with decorative invented values.
"""
import datetime
import io
import math
import os
import time
from functools import lru_cache
from PIL import Image,ImageDraw
from render import BG,FG,DIM,GRAY,CYAN,MESH,ORDER,font
from background import surface
from palette import PRIMARY,blend

# Almost all source tile vertices are distinct. Project only visible tiles,
# avoiding a full-sphere temporary point array and a second indexing pass.
FACES=[(tile,tuple(sum(v[i] for v in tile)/len(tile) for i in range(3))) for tile in MESH]
GLOBE_INKS=[tuple(round(v*(.2+.8*i/255)) for v in PRIMARY) for i in range(256)]


def row_cells(left,right,weights,gap=4):
    """Bound each value to its own column, including at narrow pane widths."""
    span=max(0,right-left);total=sum(weights);cursor=left
    for weight in weights:
        end=cursor+span*weight/total
        yield cursor,max(cursor,end-gap)
        cursor=end


@lru_cache(maxsize=512)
def text_stamp(value,face,ink):
    box=face.getbbox(value)
    stamp=Image.new('RGBA',(max(1,round(text_width(value,face))+3),max(1,box[3]+3)))
    ImageDraw.Draw(stamp).text((0,0),value,font=face,fill=ink)
    return stamp


@lru_cache(maxsize=2048)
def text_width(value,face):
    return face.getlength(value)


@lru_cache(maxsize=1024)
def fit_text(value,face,available):
    if text_width(value,face)<=available:return value
    while value and text_width(value+'…',face)>available:value=value[:-1]
    return value+'…' if value else ''


@lru_cache(maxsize=2)
def native_globe_inks(mode):
    # This is ImageDraw.polygon's own color conversion and C primitive. Keep
    # the public polygon path below for Pillow versions without that interface.
    if mode not in ('RGB','RGBA'):return None
    try:
        probe=ImageDraw.Draw(Image.new(mode,(1,1)))
        return tuple(probe._getink(ink)[0] for ink in GLOBE_INKS)
    except (AttributeError,TypeError):return None


def draw_globe(d,width,height,elapsed):
    # Keep the globe below the endpoint caption and above the traffic header
    # even when the user widens the network pane independently of its height.
    radius=min(width*.42,height*.19);cx=width/2;cy=height*.43
    angle=elapsed*2*math.pi/45;tilt=.630
    ca,sa,ct,st=math.cos(angle),math.sin(angle),math.cos(tilt),math.sin(tilt)
    ax=ca*radius;az=sa*radius
    bx=sa*st*radius;by=ct*radius;bz=-ca*st*radius
    dx=-sa*ct;dy=st;dz=ca*ct
    inks=native_globe_inks(d.mode)
    polygon=getattr(getattr(d,'draw',None),'draw_polygon',None) if inks is not None else None
    for face,(x,y,z) in FACES:
        depth=x*dx+y*dy+z*dz
        if depth>0:
            # Front-face tiles don't overlap in orthographic projection. Draw
            # only their outlines, not a redundant opaque fill and depth sort.
            points=[(cx+x*ax+z*az,cy-(x*bx+y*by+z*bz)) for x,y,z in face]
            index=min(255,round(depth*255))
            if polygon is not None:
                try:
                    polygon(points,inks[index],0,1)
                    continue
                except (AttributeError,TypeError):polygon=None
            d.polygon(points,outline=GLOBE_INKS[index])


def curve_points(values,timestamps,now,box,maximum=100,pixels_per_second=20):
    """Smoothie-style horizontal-tangent cubics on actual sample times.

    Render one sample behind real time: both endpoints are known as they scroll
    into view. Timestamp drift cannot make the graph jump at second boundaries.
    """
    x0,y0,x1,y1=box;right_time=now-1.1
    samples=[]
    for stamp,value in zip(timestamps,values):
        if value is None:continue
        samples.append((x1-(right_time-stamp)*pixels_per_second,
                        y1-(y1-y0)*max(-1,min(1,value/maximum))))
    output=[]
    for a,b in zip(samples,samples[1:]):
        if b[0]<x0 or a[0]>x1:continue
        mid=(a[0]+b[0])/2
        for i in range(13):
            t=i/12;u=1-t
            x=u**3*a[0]+3*u*u*t*mid+3*u*t*t*mid+t**3*b[0]
            y=u**3*a[1]+3*u*u*t*a[1]+3*u*t*t*b[1]+t**3*b[1]
            if x0<=x<=x1:output.append((x,y))
    return output


def render_column(kind,width,height,data,elapsed,now=None,*,raster=False,_motion=True,_wall_clock=None):
    image=surface((width,height),BG);d=ImageDraw.Draw(image)
    unit=height/70;pad=max(6,round(unit*.9));left=pad;right=width-pad
    # The CSS scales text with the viewport. Large fixed floors collided with
    # adjacent module rows after the optional keyboard reduced column height.
    normal=font(max(11,round(1.6*unit)))
    small=font(max(10,round(1.4*unit)))
    light=font(max(12,round(1.8*unit)))
    now=time.monotonic() if now is None else now
    def text(x,y,value,ink=FG,f=normal,max_width=None):
        value=fit(value,f,min(max_width if max_width is not None else right-x,right-x))
        stamp=text_stamp(str(value),f,ink)
        if image.mode == 'RGBA':image.alpha_composite(stamp,(round(x),round(y)))
        else:image.paste(stamp,(round(x),round(y)),stamp)
    def fit(value,face,available):
        return fit_text(str(value),face,available)
    def rule(y):
        d.line((left,y,right,y),fill=DIM)
        d.line((left,y-4,left,y+3),fill=DIM);d.line((right,y-4,right,y+3),fill=DIM)
    def heading(y,label,detail=''):
        rule(y)
        label=fit(label,normal,(right-left)*(.6 if detail else 1))
        text(left+3,y+4,label)
        if detail:
            available=max(0,right-left-3-text_width(label,normal)-12)
            detail=fit(detail,small,available)
            text(right-text_width(detail,small),y+5,detail,GRAY,small)
    def graph(values,box,maximum=100,ink=FG):
        if not _motion:return
        stamps=data.get('sample_times',[now-len(values)+1+i for i in range(len(values))])
        points=curve_points(values,stamps,now,box,maximum)
        if len(points)>1:d.line(points,fill=ink,width=max(1,round(unit*.17)))
    info=data.get('details',{})
    if kind=='system':
        heading(3,'PANEL','SYSTEM')
        wall_clock=_wall_clock if _wall_clock is not None else datetime.datetime.now()
        clock=wall_clock.strftime('%H : %M : %S')
        clockfont=font(max(15,round(unit*4)),'light')
        text((width-text_width(clock,clockfont))/2,height*.035,clock,f=clockfont)
        y=height*.135;rule(y)
        seconds=int(data['uptime']);uptime=f'{seconds//3600}:{seconds//60%60:02d}'
        fields=[(wall_clock.strftime('%Y'),wall_clock.strftime('%b %d').upper()),('UPTIME',uptime),
                ('TYPE',info.get('system','Linux')),('POWER',info.get('power','--'))]
        for i,(name,value) in enumerate(fields):
            x=left+i*(right-left)/4;text(x,y+6,name,GRAY,small)
            text(x,y+max(unit*2.1,small.size+5),value,f=light,max_width=(right-left)/4-5)
        y=height*.22;heading(y,'MANUFACTURER','MODEL')
        text(left,y+unit*2.2,fit(info.get('manufacturer','--'),small,width*.48),GRAY,small)
        model=fit(info.get('hardware','--'),small,width*.4)
        text(width*.56,y+unit*2.2,model,GRAY,small)
        y=height*.285;heading(y,'CPU USAGE',info.get('model','--'))
        cpus=data['cpus'];divide=max(1,len(cpus)//2)
        for group,indices in enumerate([range(divide),range(divide,len(cpus))]):
            y0=y+unit*3.4+group*height*.09;y1=y0+height*.072
            indices=list(indices)
            if not indices:continue
            text(left,y0,f'# {indices[0]+1} - {indices[-1]+1}',f=small)
            valid=[cpus[i] for i in indices if cpus[i] is not None]
            avg=f'Avg. {sum(valid)/len(valid):.0f}%' if valid else 'Avg. --%'
            text(left,y0+unit*1.7,avg,GRAY,small)
            x0=left+(right-left)*.25
            for i in indices:graph([v[i] if i<len(v) else None for v in data['history']],(x0,y0,right,y1))
            d.line((x0,y0-3,right,y0-3),fill=DIM);d.line((x0,y1+3,right,y1+3),fill=DIM)
        y=height*.51;rule(y)
        mhz=info.get('mhz',[]);temp=info.get('temperature')
        fields=[('TEMP',f'{temp:.0f}°C' if temp is not None else '--'),
                ('SPD',f'{min(mhz)/1000:.2f}GHz' if mhz else '--'),
                ('MAX',f'{max(mhz)/1000:.2f}GHz' if mhz else '--'),('TASKS',info.get('tasks','--'))]
        for i,(label,value) in enumerate(fields):
            x=left+i*(right-left)/4;text(x,y+4,label,f=small)
            text(x,y+unit*2.3,value,GRAY,small,max_width=(right-left)/4-5)
        mem=data['memory'];total=mem['MemTotal'];active=mem.get('Active',total-mem['MemAvailable'])
        y=height*.58;heading(y,'MEMORY',f'{active/2**30:.1f} / {total/2**30:.1f} GiB')
        used=min(440,round(440*active/total));available=min(440-used,round(440*max(0,mem['MemAvailable']-mem['MemFree'])/total))
        colors=[blend(.1)]*440
        for i in ORDER[:used]:colors[i]=FG
        for i in ORDER[used:used+available]:colors[i]=blend(.3)
        for i,color in enumerate(colors):
            col,row=divmod(i,11);x=left+col*(right-left)/40;yy=y+unit*3+row*height*.009
            d.rectangle((x,yy,x+max(1,(right-left)/40*.28),yy+max(1,height*.003)),fill=color)
        y=height*.735
        swap=mem.get('SwapTotal',0);usedswap=swap-mem.get('SwapFree',0)
        text(left,y,'SWAP',f=small)
        x0=left+width*.17;x1=right-width*.18
        d.line((x0,y+unit,x1,y+unit),fill=DIM,width=2)
        d.line((x0,y+unit,x0+(x1-x0)*(usedswap/swap if swap else 0),y+unit),fill=FG,width=3)
        text(x1+3,y,f'{usedswap/2**30:.1f} GiB',GRAY,small)
        y=height*.78;heading(y,'TOP PROCESSES','PID | NAME | CPU | MEM')
        processes=info.get('processes',[])
        weights=(18,44,20,18)
        if width<220 and processes:
            # At mobile widths, shorten names before numeric process values.
            pid_width=max(text_width(str(p['pid']),small) for p in processes)+5
            cpu_width=max(text_width(f"{p['cpu']:.1f}%" if p['cpu'] is not None else '--',small) for p in processes)+5
            mem_width=max(text_width(f"{p['memory']:.1f}%",small) for p in processes)+5
            name_width=max(1,right-left-pid_width-cpu_width-mem_width)
            weights=(pid_width,name_width,cpu_width,mem_width)
        process_cells=list(row_cells(left,right,weights))
        for i,process in enumerate(processes):
            yy=y+unit*3+i*height*.03
            cpu=process['cpu']
            values=(process['pid'],process['name'],f'{cpu:.1f}%' if cpu is not None else '--',
                    f"{process['memory']:.1f}%")
            for index,((x0,x1),value) in enumerate(zip(process_cells,values)):
                value=fit(value,small,x1-x0)
                x=x1-text_width(value,small) if index>=2 else x0
                text(x,yy,value,f=small,max_width=x1-x)
    else:
        heading(3,'PANEL','NETWORK')
        y=max(height*.04,normal.size+12);heading(y,'NETWORK STATUS','Interface: '+info.get('interface','--'))
        values=[('STATE',info.get('state','--')),('IPv4',info.get('address','--')),('PING','--')]
        # mod_netstat.css spans IPv4 over the middle two of four grid columns.
        for (x,x1),(label,value) in zip(row_cells(left,right,(1,2,1)),values):
            text(x,y+unit*3,label,GRAY,small,max_width=x1-x)
            text(x,y+unit*5,value,f=light,max_width=x1-x)
        y=height*.18;heading(y,'WORLD VIEW','GLOBAL NETWORK MAP')
        text(left,y+unit*2.7,'ENDPOINT LAT/LON',GRAY,small)
        text(right-width*.19,y+unit*2.7,'--, --',GRAY,small)
        draw_globe(d,width,height,elapsed)
        y=height*.66;heading(y,'NETWORK TRAFFIC','UP / DOWN, MiB/s')
        total=data.get('net_totals',[0,0]);text(left,y+unit*2.6,'TOTAL',GRAY,small)
        text(width*.35,y+unit*2.6,f'{total[1]/2**20:.0f} MiB OUT, {total[0]/2**20:.0f} MiB IN',GRAY,small)
        x0=left;y0=height*.76;x1=right;y1=height*.96;middle=(y0+y1)/2
        for fraction in (0,.25,.5,.75,1):d.line((x0,y0+(y1-y0)*fraction,x1,y0+(y1-y0)*fraction),fill=DIM)
        for fraction in (0,.25,.5,.75,1):d.line((x0+(x1-x0)*fraction,y0,x0+(x1-x0)*fraction,y1),fill=DIM)
        maximum=max(1024,max((abs(v) for row in data['net_history'] for v in row if v is not None),default=0))
        for i,sign in [(0,1),(1,-1)]:
            graph([None if row[i] is None else row[i]*sign for row in data['net_history']],
                  (x0,y0,x1,middle),maximum)
        text(right-40,y0-20,f'{maximum/2**20:.2f}',GRAY,small)
    # Upstream activates successive module rows every 500 ms; each fades for
    # 500 ms. Rendering a column as one tmux pane preserves sub-cell geometry.
    sections=([0,.135,.22,.285,.58,.78,1] if kind=='system' else [0,.18,.66,1])
    for i,(start,end) in enumerate(zip(sections,sections[1:])):
        fade=max(0,min(1,(elapsed-(i+1)*.5)/.5))
        if fade<1:
            box=(0,round(start*height),width,round(end*height))
            crop=image.crop(box)
            image.paste(Image.blend(surface(crop.size,BG),crop,fade),box[:2])
    if raster:return image
    output=io.BytesIO();image.save(output,format='PNG',compress_level=2)
    return output.getvalue()


def draw_system_motion(image,data,now):
    """Draw system curves over a completed, unfaded static surface."""
    width,height=image.size;d=ImageDraw.Draw(image)
    unit=height/70;left=max(6,round(unit*.9));right=width-left
    def graph(values,box,maximum=100):
        stamps=data.get('sample_times',[now-len(values)+1+i for i in range(len(values))])
        points=curve_points(values,stamps,now,box,maximum)
        if len(points)>1:d.line(points,fill=FG,width=max(1,round(unit*.17)))
    cpus=data['cpus'];divide=max(1,len(cpus)//2)
    for group,indices in enumerate((range(divide),range(divide,len(cpus)))):
        y0=height*.285+unit*3.4+group*height*.09;y1=y0+height*.072
        x0=left+(right-left)*.25
        for i in indices:
            graph([v[i] if i<len(v) else None for v in data['history']],(x0,y0,right,y1))


class ColumnRenderer:
    """Cache one system surface for one worker's immutable metrics snapshot.

    Metrics.sample returns a new dictionary on each sample. Keeping that object
    alive prevents id reuse; callers must replace it when data changes. Large
    canvases, the startup fade and the network column use the uncached path.
    """
    MAX_CACHE_BYTES=8*1024*1024

    def __init__(self):
        self._key=None;self._data=None;self._base=None

    @property
    def cache_bytes(self):
        return self._base.width*self._base.height*len(self._base.getbands()) if self._base is not None else 0

    def raster(self,kind,width,height,data,elapsed,now=None):
        channels=4 if os.environ.get('EDEX_GRID_BACKGROUND')=='1' else 3
        if kind!='system' or elapsed<4 or width*height*channels>self.MAX_CACHE_BYTES:
            self._key=None;self._data=None;self._base=None
            return render_column(kind,width,height,data,elapsed,now,raster=True)
        clock=datetime.datetime.now();second=clock.replace(microsecond=0)
        key=(kind,width,height,channels,second)
        if key!=self._key or data is not self._data:
            self._base=None
            self._base=render_column(kind,width,height,data,elapsed,now,raster=True,
                                     _motion=False,_wall_clock=clock)
            self._key=key;self._data=data
        image=self._base.copy()
        draw_system_motion(image,data,time.monotonic() if now is None else now)
        return image
