"""Pinned TRON palette and opaque equivalents of upstream CSS alpha colors."""
import json
import math
from pathlib import Path

THEME=json.loads((Path(__file__).parent/'references/tron.json').read_text())
BG=THEME['colors']['light_black']
PRIMARY=tuple(THEME['colors'][key] for key in ('r','g','b'))
FG='#'+''.join(f'{value:02x}' for value in PRIMARY)


def blend(alpha,background=BG,foreground=PRIMARY):
    base=bytes.fromhex(background.removeprefix('#'))
    return '#'+''.join(f'{math.floor(a*alpha+b*(1-alpha)+.5):02x}' for a,b in zip(foreground,base))


DIM=blend(.3)
MUTED=blend(.5)
SELECTION=blend(.1)


def terminal_colors():
    # terminal.class.js: color(base).grayscale().mix(themeColor, 0.3).
    # color's grayscale uses 0.3 R + 0.59 G + 0.11 B; black is explicit.
    defaults=['#2e3436','#cc0000','#4e9a06','#c4a000','#3465a4','#75507b','#06989a','#d3d7cf',
              '#555753','#ef2929','#8ae234','#fce94f','#729fcf','#ad7fa8','#34e2e2','#eeeeec']
    colors=[]
    for value in defaults:
        r,g,b=bytes.fromhex(value[1:]);grey=r*.3+g*.59+b*.11
        colors.append('#'+''.join(f'{math.floor(grey*.7+channel*.3+.5):02x}' for channel in PRIMARY))
    colors[0]=THEME['colors']['black']
    return colors
