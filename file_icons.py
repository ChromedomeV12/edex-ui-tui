"""Load selected original eDEX SVG icons as Kitty virtual placements for Yazi.

Yazi owns navigation and draws normal placeholder cells via its UI API. Images
go only to this isolated tmux session's attached, user-owned client TTYs. This
avoids letting Yazi's terminal probes pass through into the interactive shell.
"""
import io
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
from PIL import Image as Raster
from protocol import Image,DIACRITICS
from render import FG,BG,ROOT
from tmux_control import query


class Icons:
    def __init__(self):
        self.icons=json.loads((ROOT/'assets/file-icons.json').read_text())
        self.ids={name:secrets.randbelow(0xfffffe)+1 for name in self.icons}
        self.pngs={};self.loaded=set()

    def environment(self):
        return dict(EDEX_ICON_IDS=','.join(f'{name}={value}' for name,value in self.ids.items()),
                    EDEX_ICON_MARKS=''.join(DIACRITICS[:8]))

    def prepare(self):
        geometry=query('display-message','-p','#{client_cell_width},#{client_cell_height}') or '9,20'
        try:cw,ch=map(int,geometry.split(','))
        except ValueError:cw,ch=9,20
        width,height=6*(cw or 9),3*(ch or 20);side=max(16,min(width,height)-4)
        for name,icon in self.icons.items():
            svg=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {icon["width"]} {icon["height"]}" '
                 f'fill="{FG}">{icon["svg"]}</svg>').encode()
            png=subprocess.run(['rsvg-convert','-w',str(side),'-h',str(side)],input=svg,
                               capture_output=True,check=True,timeout=5).stdout
            art=Raster.open(io.BytesIO(png)).convert('RGBA')
            canvas=Raster.new('RGB',(width,height),BG)
            canvas.paste(art,((width-art.width)//2,(height-art.height)//2),art)
            output=io.BytesIO();canvas.save(output,format='PNG')
            self.pngs[name]=output.getvalue()

    def clients(self):
        result=query('list-clients','-F','#{client_tty}|#{client_pid}|#{client_created}')
        return None if result is None else [line for line in result.splitlines() if line]

    def refresh(self):
        clients=self.clients()
        if clients is None:return
        self.loaded.intersection_update(clients)
        for signature in clients:
            if signature in self.loaded:continue
            path=signature.split('|')[0]
            try:
                info=os.stat(path)
                if not stat.S_ISCHR(info.st_mode) or info.st_uid!=os.getuid():continue
                # Kitty's outer buffer is shared by the isolated tmux panes.
                # No input is read, no global terminal is searched or modified.
                with open(path,'wb',buffering=65536) as stream:
                    for name,png in self.pngs.items():
                        image=Image(stream,image_id=self.ids[name],tmux=False)
                        image.pixels(png);image.send(a='p',U=1,p=1,c=6,r=3)
                    stream.flush()
                self.loaded.add(signature)
                query('refresh-client','-t',path)
            except OSError:continue
