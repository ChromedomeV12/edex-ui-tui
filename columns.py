"""eDEX's two original mod_column sections, rasterized in separate tmux panes.

Module ordering/labels/geometry follow the pinned CSS and class DOM. Missing
telemetry is shown as --, never replaced with decorative invented values.
"""
import datetime
import io
import math
import time
from functools import lru_cache
from PIL import Image,ImageDraw
from render import BG,FG,DIM,GRAY,CYAN,MESH,ORDER,font

# Shared boundary vertices occur in several adjacent tiles. Rotate each unique
# vertex once, rather than repeating all of the projection math per polygon.
_vertex_ids={};VERTICES=[];FACES=[]
for tile in MESH:
    face=[]
    for vertex in tile:
        if vertex not in _vertex_ids:
            _vertex_ids[vertex]=len(VERTICES);VERTICES.append(vertex)
        face.append(_vertex_ids[vertex])
    FACES.append((face,tuple(sum(v[i] for v in tile)/len(tile) for i in range(3))))
GLOBE_INKS=[tuple(round(v*(.2+.8*i/255)) for v in (170,207,209)) for i in range(256)]


@lru_cache(maxsize=512)
def text_stamp(value,face,ink):
    box=face.getbbox(value)
    stamp=Image.new('RGBA',(max(1,round(face.getlength(value))+3),max(1,box[3]+3)))
    ImageDraw.Draw(stamp).text((0,0),value,font=face,fill=ink)
    return stamp


def draw_globe(d,width,height,elapsed):
    # Keep the globe below the endpoint caption and above the traffic header
    # even when the user widens the network pane independently of its height.
    radius=min(width*.42,height*.19);cx=width/2;cy=height*.43
    angle=elapsed*2*math.pi/45;tilt=.630
    ca,sa,ct,st=math.cos(angle),math.sin(angle),math.cos(tilt),math.sin(tilt)
    ax=ca*radius;az=sa*radius
    bx=sa*st*radius;by=ct*radius;bz=-ca*st*radius
    dx=-sa*ct;dy=st;dz=ca*ct
    projected=[(cx+x*ax+z*az,cy-(x*bx+y*by+z*bz)) for x,y,z in VERTICES]
    for face,(x,y,z) in FACES:
        depth=x*dx+y*dy+z*dz
        if depth>0:
            # Front-face tiles don't overlap in orthographic projection. Draw
            # only their outlines, not a redundant opaque fill and depth sort.
            d.polygon([projected[i] for i in face],outline=GLOBE_INKS[min(255,round(depth*255))])


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


def render_column(kind,width,height,data,elapsed,now=None,*,raster=False):
    image=Image.new('RGB',(width,height),BG);d=ImageDraw.Draw(image)
    unit=height/70;pad=max(6,round(unit*.9));left=pad;right=width-pad
    normal=font(max(15,round(1.6*unit)))
    small=font(max(13,round(1.4*unit)))
    light=font(max(15,round(1.8*unit)))
    now=time.monotonic() if now is None else now
    def text(x,y,value,ink=FG,f=normal,max_width=None):
        value=fit(value,f,min(max_width if max_width is not None else right-x,right-x))
        stamp=text_stamp(str(value),f,ink)
        image.paste(stamp,(round(x),round(y)),stamp)
    def fit(value,face,available):
        value=str(value)
        if face.getlength(value)<=available:return value
        while value and face.getlength(value+'…')>available:value=value[:-1]
        return value+'…' if value else ''
    def rule(y):
        d.line((left,y,right,y),fill=DIM)
        d.line((left,y-4,left,y+3),fill=DIM);d.line((right,y-4,right,y+3),fill=DIM)
    def heading(y,label,detail=''):
        rule(y)
        label=fit(label,normal,(right-left)*(.6 if detail else 1))
        text(left+3,y+4,label)
        if detail:
            available=max(0,right-left-3-normal.getlength(label)-12)
            detail=fit(detail,small,available)
            text(right-small.getlength(detail),y+5,detail,GRAY,small)
    def graph(values,box,maximum=100,ink=FG):
        stamps=data.get('sample_times',[now-len(values)+1+i for i in range(len(values))])
        points=curve_points(values,stamps,now,box,maximum)
        if len(points)>1:d.line(points,fill=ink,width=max(1,round(unit*.17)))
    info=data.get('details',{})
    if kind=='system':
        heading(3,'PANEL','SYSTEM')
        wall_clock=datetime.datetime.now()
        clock=wall_clock.strftime('%H : %M : %S')
        clockfont=font(max(15,round(unit*4)),'light')
        text((width-d.textlength(clock,font=clockfont))/2,height*.035,clock,f=clockfont)
        y=height*.135;rule(y)
        seconds=int(data['uptime']);uptime=f'{seconds//3600}:{seconds//60%60:02d}'
        fields=[(wall_clock.strftime('%Y'),wall_clock.strftime('%b %d').upper()),('UPTIME',uptime),
                ('TYPE',info.get('system','Linux')),('POWER',info.get('power','--'))]
        for i,(name,value) in enumerate(fields):
            x=left+i*(right-left)/4;text(x,y+6,name,GRAY,small)
            text(x,y+unit*2.1,value,f=light,max_width=(right-left)/4-5)
        y=height*.22;heading(y,'MANUFACTURER','MODEL')
        text(left,y+unit*2.2,fit(info.get('manufacturer','--'),small,width*.48),GRAY,small)
        model=fit(info.get('hardware','--'),small,width*.4)
        text(width*.56,y+unit*2.2,model,GRAY,small)
        y=height*.285;heading(y,'CPU USAGE',info.get('model','--')[:24])
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
        colors=['#152023']*440
        for i in ORDER[:used]:colors[i]=FG
        for i in ORDER[used:used+available]:colors[i]='#374448'
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
        for i,process in enumerate(info.get('processes',[])):
            yy=y+unit*3+i*height*.03
            text(left,yy,process['pid'],f=small,max_width=width*.16-5)
            text(left+width*.16,yy,process['name'],f=small,max_width=width*.46-8)
            cpu=process['cpu'];text(width*.66,yy,f'{cpu:.1f}%' if cpu is not None else '--',f=small)
            text(width*.84,yy,f"{process['memory']:.1f}%",f=small)
    else:
        heading(3,'PANEL','NETWORK')
        y=height*.04;heading(y,'NETWORK STATUS','Interface: '+info.get('interface','--'))
        for i,(label,value) in enumerate([('STATE',info.get('state','--')),('IPv4',info.get('address','--')),('PING','--')]):
            x=left+i*(right-left)/3;text(x,y+unit*3,label,GRAY,small)
            text(x,y+unit*5,value,f=light,max_width=(right-left)/3-5)
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
            image.paste(Image.blend(Image.new('RGB',crop.size,BG),crop,fade),box[:2])
    if raster:return image
    output=io.BytesIO();image.save(output,format='PNG',compress_level=2)
    return output.getvalue()
