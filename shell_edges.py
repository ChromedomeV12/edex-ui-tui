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


def contour(width,height,shell_box,viewport_height):
    stroke=max(1,viewport_height*.0018)
    left,top,right,bottom=shell_box
    padding=round(viewport_height*.0074)
    L=max(1,left-padding-stroke);R=min(width-2,right+padding+stroke)
    B=min(height-2,bottom+padding+stroke)
    clip=min(15,max(0,left-L+B-bottom-1.5*stroke))
    return _ring_polygons(L,1,R,B,stroke,15,clip)


def frame_image(width,height,shell_box,viewport_height):
    """Keep frame pixels outside the native shell's exclusive bounds."""
    left,top,right,bottom=shell_box
    outer,inner=contour(width,height,shell_box,viewport_height)
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
        changed=signature!=self.signature or not self.visible
        if changed:
            # Geometry and popup masks can change the alpha surface. Replace
            # the owned root instead of compositing frames over an old mask;
            # a newly attached terminal also needs a complete root upload.
            if self.image.loaded:
                stream=self.image.stream
                self.image.close();self.image=Image(stream)
            raster=frame_image(width,height,box,viewport_height)
            # tmux reserves a separator row between tabs and shell. Cover that
            # cell-sized gap with the shell surface, not the desktop dot field.
            from palette import BG
            surface=Raster.new('RGBA',raster.size,(0,0,0,0))
            draw=ImageDraw.Draw(surface)
            draw.polygon(contour(width,height,box,viewport_height)[0],fill=BG)
            # Protect both native shell cells and the tab image. Fill only the
            # otherwise empty inset/separator pixels inside the closed contour.
            draw.rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=(0,0,0,0))
            draw.rectangle((cw,0,cw+cols*cw-1,rows*ch-1),fill=(0,0,0,0))
            raster=Raster.alpha_composite(surface,raster)
            if popup:
                try:
                    px,py,pw,ph=map(int,popup.split('/'))
                    ImageDraw.Draw(raster).rectangle(((px-tl+1)*cw,(py-tt)*ch,
                                                     (px+pw-tl+1)*cw-1,(py+ph-tt)*ch-1),
                                                    fill=(0,0,0,0))
                except ValueError:return
            output=io.BytesIO();raster.save(output,format='PNG')
            self.image.pixels(output.getvalue())
            self.signature=signature;self.visible=True
        if changed or recover:
            # Replacing the virtual parent placement can discard its relative
            # children. Reattach after its heartbeat without uploading pixels.
            self.image.send(a='p',p=1,P=parent[0].id,Q=parent[0].placement_id,
                            H=-1,V=0,c=tw+2,r=st+sh-tt+2,z=1)
            self.image.stream.flush()
            from tmux_control import query
            query('set-option','-t','edex','@edex-frame-popup-ready',popup)

    def close(self):self.image.close()
