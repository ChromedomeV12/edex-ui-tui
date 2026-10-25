"""Opt-in clipped frame anchored to the existing shell tab image."""
import io

from PIL import Image as Raster, ImageDraw
from border_frame import _coverage, _ring_polygons, STROKE, STROKE_ALPHA
from protocol import Image


def install():
    from launch import tmux
    tmux('has-session','-t','=edex')
    shell=tmux('show-options','-qv','-t','edex','@edex-shell')
    if not shell:raise RuntimeError('No project shell')
    if tmux('show-options','-qv','-t','edex','@edex-shell-frame')=='1':return
    # One empty row, no process. Reuse native separator columns for the sides.
    gutter=tmux('split-window','-d','-v','-t',shell,'-l','1','-P','-F','#{pane_id}','')
    tmux('select-pane','-t',gutter,'-T','Shell padding')
    tmux('set-option','-t','edex','@edex-shell-padding',gutter)
    tmux('set-option','-t','edex','@edex-shell-frame','1')
    tmux('set-option','-w','-t',shell,'pane-border-style','fg=#000000,bg=default')
    tmux('set-option','-w','-t',shell,'pane-active-border-style','fg=#000000,bg=default')


def frame_image(width,height,shell_box,viewport_height):
    """Keep frame pixels outside the native shell's exclusive bounds."""
    stroke=max(1,viewport_height*.0018)
    left,top,right,bottom=shell_box
    clip=min(15,max(0,left+height-bottom-1.5*stroke))
    outer,inner=_ring_polygons(1,1,width-2,height-2,stroke,15,clip)
    alpha=_coverage(width,height,outer,inner).point(lambda value:round(value*STROKE_ALPHA/255))
    image=Raster.new('RGBA',(width,height),(*STROKE,0));image.putalpha(alpha)
    ImageDraw.Draw(image).rectangle((left,top,right-1,bottom-1),fill=(0,0,0,0))
    return image


class ShellFrame:
    def __init__(self,stream):
        self.image=Image(stream);self.signature=None;self.visible=False

    def update(self,parent,raw,cols,rows,cw,ch,viewport_height,recover=False,hidden=False,padding=None,popup=''):
        if hidden:
            if self.visible:self.image.send(a='d',d='i')
            self.visible=False;self.signature=None;return
        try:
            panes={p[0]:tuple(map(int,p[1:])) for item in raw.split('~') if item
                   for p in [item.split('/')]}
            # Caller prepends the active shell id. Parent image starts at tab (0,0).
            shell_id,tab_id=parent[1:]
            sl,st,sw,sh=panes[shell_id];tl,tt,tw,th=panes[tab_id]
        except (ValueError,KeyError):return
        if padding in panes and panes[padding][3]!=1:
            from tmux_control import query
            query('resize-pane','-t',padding,'-y','1')
            return  # Wait for the next batched layout before drawing.
        width=(tw+2)*cw;height=(st+sh-tt+2)*ch
        box=((sl-tl+1)*cw,(st-tt)*ch,(sl-tl+sw+1)*cw,(st-tt+sh)*ch)
        signature=(width,height,box,viewport_height,parent[0].id,popup)
        if recover or signature!=self.signature or not self.visible:
            raster=frame_image(width,height,box,viewport_height)
            if popup:
                try:
                    px,py,pw,ph=map(int,popup.split('/'))
                    ImageDraw.Draw(raster).rectangle(((px-tl+1)*cw,(py-tt)*ch,
                                                     (px+pw-tl+1)*cw-1,(py+ph-tt)*ch-1),
                                                    fill=(0,0,0,0))
                except ValueError:return
            output=io.BytesIO();raster.save(output,format='PNG')
            same_size=self.signature is not None and self.signature[:2]==signature[:2]
            self.image.pixels(output.getvalue(),update=self.image.loaded and same_size)
            self.image.send(a='p',p=1,P=parent[0].id,Q=parent[0].placement_id,
                            H=-1,V=0,c=tw+2,r=st+sh-tt+2)
            self.signature=signature;self.visible=True
            self.image.stream.flush()
            from tmux_control import query
            query('set-option','-t','edex','@edex-frame-popup-ready',popup)

    def close(self):self.image.close()
