"""Source-derived grid dimensions, colors, and reproducible native tile."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import unittest
import io
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from background import ROOT, grid_tile


class BackgroundTest(unittest.TestCase):
    def test_popup_masks_only_covered_frame_and_close_restores_it(self):
        from shell_edges import ShellFrame
        from protocol import Image as Transport
        stream=io.BytesIO();frame=ShellFrame(stream);anchor=Transport(stream,image_id=42,tmux=False)
        raw='%0/36/3/138/29~%4/36/0/138/2~'
        with patch.object(frame.image,'pixels') as pixels,patch('tmux_control.query'):
            def draw(popup):
                frame.update((anchor,'%0','%4'),raw,137,2,9,20,1080,popup=popup)
                return Image.open(io.BytesIO(pixels.call_args.args[0])).copy()
            normal=draw('')
            covered=draw('21/6/167/36')
            self.assertEqual(normal.crop((0,0,1260,100)).tobytes(),covered.crop((0,0,1260,100)).tobytes())
            self.assertEqual(covered.crop((0,120,1260,680)).getchannel('A').getextrema(),(0,0))
            restored=draw('')
            self.assertEqual(normal.tobytes(),restored.tobytes())

    def test_frame_leaves_shell_pixels_untouched(self):
        from shell_edges import frame_image
        frame=frame_image(1000,600,(9,60,991,560),1080)
        self.assertEqual(frame.crop((9,60,991,560)).getchannel('A').getextrema(),(0,0))
        self.assertGreater(frame.getchannel('A').getextrema()[1],0)

    def test_instrument_leaves_background_transparent(self):
        from columns import render_column
        from test_port import fixture
        with patch.dict(os.environ, EDEX_GRID_BACKGROUND='1'):
            column=render_column('network-column',300,680,fixture(),5,now=20,raster=True)
        self.assertEqual(column.mode,'RGBA')
        self.assertEqual(column.getchannel('A').getextrema(),(0,255))
        self.assertEqual(column.getpixel((0,0))[3],0)

    @unittest.skipUnless(sys.platform == 'linux', 'keyboard uses Linux terminal input')
    def test_idle_keyboard_leaves_background_transparent(self):
        from keyboard import Keyboard
        with patch.dict(os.environ, EDEX_GRID_BACKGROUND='1'):
            keyboard=Image.open(io.BytesIO(Keyboard().png(1000,300)))
        self.assertEqual(keyboard.mode,'RGBA')
        self.assertEqual(keyboard.getchannel('A').getextrema(),(0,255))
        self.assertEqual(keyboard.getpixel((0,0))[3],0)

    def test_raw_rgba_frames_use_32_bit_format_and_replace_previous_frame(self):
        from protocol import Image as Transport
        stream=io.BytesIO();transport=Transport(stream,image_id=42,tmux=False)
        transport.pixels(b'fixture',size=(1,1),channels=4)
        transport.pixels(b'fixture',True,size=(1,1),channels=4)
        value=stream.getvalue()
        self.assertIn(b'f=32',value)
        self.assertIn(b'r=1,X=1',value)

    @unittest.skipUnless(sys.platform == 'linux', 'private tmux surface test')
    def test_grid_is_window_scoped_and_shell_is_opaque(self):
        from launch import configure_grid_surface
        binary = shutil.which('tmux')
        self.assertIsNotNone(binary)
        socket = 'edex-grid-surface-' + str(os.getpid())
        def tm(*args):
            return subprocess.check_output([binary, '-L', socket, '-f', '/dev/null', *args], text=True).strip()
        try:
            shell = tm('new-session', '-d', '-s', 'grid', '-P', '-F', '#{pane_id}', 'sleep', '30')
            with patch.dict(os.environ, EDEX_GRID_BACKGROUND='1'):
                configure_grid_surface(shell, 'grid', run=tm)
            self.assertIn('bg=default', tm('show-options', '-w', '-v', '-t', shell, 'window-style'))
            self.assertIn('bg=#05080d', tm('show-options', '-p', '-v', '-t', shell, 'window-style'))
            self.assertEqual(tm('show-options', '-v', '-t', 'grid', '@edex-grid-background'), '1')
        finally:
            subprocess.run([binary, '-L', socket, 'kill-server'], capture_output=True)

    def test_reference_tile_preserves_source_palette_and_square_gap(self):
        tile = grid_tile(1080)
        self.assertEqual(tile.size, (22, 22))
        colors = dict((color, count) for count, color in tile.getcolors())
        self.assertEqual(colors, {(5, 8, 13): 480, (38, 40, 40): 4})
        self.assertEqual(tile.getpixel((20, 20)), (38, 40, 40))
        self.assertEqual(tile.getpixel((19, 21)), (5, 8, 13))

    def test_asset_matches_generator_and_height_changes_pitch(self):
        stored = Image.open(ROOT/'assets/background-grid-1080.png')
        self.assertEqual(stored.tobytes(), grid_tile().tobytes())
        self.assertEqual(grid_tile(1440).size, (29, 29))
        self.assertEqual(grid_tile(720).size, (15, 15))
        for value in (0, -100, 20000):
            with self.assertRaises(ValueError):
                grid_tile(value)


if __name__ == '__main__':
    unittest.main()
