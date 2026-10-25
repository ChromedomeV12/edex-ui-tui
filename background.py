"""Static approximation of the pinned eDEX crossed-gradient background."""
import argparse
import json
import os
from pathlib import Path
import re

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent


def surface(size, background):
    """Expose Kitty's shared tile beneath instruments in the grid preset."""
    if os.environ.get('EDEX_GRID_BACKGROUND') == '1':
        return Image.new('RGBA', size, (0, 0, 0, 0))
    return Image.new('RGB', size, background)


def grid_tile(viewport_height=1080):
    if not 100 <= viewport_height <= 16384:
        raise ValueError('viewport height must be between 100 and 16384 pixels')
    css = (ROOT/'references/css/main.css').read_text()
    pitch_vh = float(re.search(r'background-size:\s*([\d.]+)vh', css)[1])
    band_vh = float(re.search(r'linear-gradient\(90deg,\s*var\(--color_light_black\)\s*([\d.]+)vh', css)[1])
    colors = json.loads((ROOT/'references/tron.json').read_text())['colors']
    pitch = max(1, round(viewport_height*pitch_vh/100))
    band = min(pitch, max(0, round(viewport_height*band_vh/100)))
    tile = Image.new('RGB', (pitch, pitch), colors['light_black'])
    if band < pitch:
        ImageDraw.Draw(tile).rectangle((band, band, pitch-1, pitch-1), fill=colors['grey'])
    return tile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--viewport-height', type=int, default=1080)
    parser.add_argument('--output', type=Path, default=ROOT/'assets/background-grid-1080.png')
    parser.add_argument('--launch', nargs=argparse.REMAINDER, help='Launch Kitty with this grid and the supplied command')
    args = parser.parse_args()
    try:
        tile = grid_tile(args.viewport_height)
    except ValueError as error:
        parser.error(str(error))
    if args.launch is not None:
        if not args.output.is_file():
            parser.error('grid asset is missing; run background.py once to generate it')
        os.environ['EDEX_GRID_BACKGROUND'] = '1'
        os.execvp('kitty', ['kitty', '--class', 'edex-ui-tui', '--config', str(ROOT/'kitty-grid.conf'),
                           '-o', 'background_image='+str(args.output.resolve()), *args.launch])
        return
    tile.save(args.output, format='PNG')
    print(f'{args.output}: {tile.width}px pitch; viewport reference {args.viewport_height}px')


if __name__ == '__main__':
    main()
