"""Protocol/data/renderer contracts independent of the desktop environment."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import base64
import io
from pathlib import Path
import tempfile
import unittest
import os
import subprocess
import sys
from PIL import Image as PILImage
from metrics import Metrics
from protocol import Image,command
from render import render


def fixture():
    return dict(cpus=[10,30],history=[[10,30]]*80,network=[1024,2048],
                net_history=[[1024,2048]]*80,uptime=300,
                memory=dict(MemTotal=8*2**30,MemAvailable=5*2**30,MemFree=2*2**30,
                            Active=3*2**30,SwapTotal=2**30,SwapFree=2**30))


class PortTests(unittest.TestCase):
    def test_tmux_read_timeout_and_server_failure_are_recoverable(self):
        from tmux_control import query
        from unittest.mock import patch
        from types import SimpleNamespace
        replies=[subprocess.TimeoutExpired(['tmux','display-message'],.5),
                 SimpleNamespace(returncode=1,stdout=''),
                 FileNotFoundError('tmux'),
                 SimpleNamespace(returncode=0,stdout='1,1,0,0\n')]
        with patch('tmux_control.subprocess.run',side_effect=replies):
            self.assertIsNone(query('display-message','-p','state'))
            self.assertIsNone(query('display-message','-p','state'))
            self.assertIsNone(query('display-message','-p','state'))
            self.assertEqual(query('display-message','-p','state'),'1,1,0,0')

    @unittest.skipUnless(sys.platform=='linux','POSIX tab input module')
    def test_tabs_use_upstream_dimensions_and_matching_hit_regions(self):
        from shell_tabs import tab_geometry,hit_tab,render_tabs
        import math
        step,height,cut=tab_geometry(1100,40,1080)
        self.assertEqual(height,31)
        self.assertAlmostEqual(cut,math.tan(math.radians(35))*height)
        for slot in range(1,6):
            self.assertEqual(hit_tab((slot-.5)*step,15,1100,40,1080),slot)
        self.assertIsNone(hit_tab(100,36,1100,40,1080))
        self.assertIsNone(hit_tab(-1,10,1100,40,1080))
        png=render_tabs(1100,40,1,[True,False,False,False,False])
        image=PILImage.open(io.BytesIO(png))
        self.assertEqual(image.size,(1100,40))
        self.assertEqual(image.getpixel((100,36)),(5,8,13))

    def test_passthrough_escaping(self):
        plain=command(dict(a='t',i=42),b'AAAA',False)
        wrapped=command(dict(a='t',i=42),b'AAAA',True)
        self.assertEqual(wrapped,b'\x1bPtmux;'+plain.replace(b'\x1b',b'\x1b\x1b')+b'\x1b\\')

    def test_bounded_root_frame_updates_and_scoped_cleanup(self):
        stream=io.BytesIO();image=Image(stream,image_id=0x123456,tmux=False)
        payload=bytes(range(256))*40
        image.pixels(payload);image.pixels(payload,True);image.close()
        value=stream.getvalue()
        self.assertIn(b'a=f',value);self.assertIn(b'r=1,X=1',value)
        self.assertNotIn(b'd=A',value)
        self.assertIn(b'd=I',value)
        chunks=value.split(b'\x1b_G')[1:]
        for chunk in chunks:
            self.assertLess(len(chunk),2200)
        first=value.split(b'\x1b_G')[1:8]
        encoded=b''.join(p.split(b';',1)[1].split(b'\x1b\\')[0] for p in first)
        self.assertEqual(base64.b64decode(encoded),payload)

    def test_lossless_rgb_transport_preserves_png_pixels(self):
        import zlib
        from columns import render_column
        data=fixture()
        raster=render_column('network-column',300,680,data,5,now=20,raster=True)
        png=render_column('network-column',300,680,data,5,now=20)
        self.assertEqual(raster.tobytes(),PILImage.open(io.BytesIO(png)).tobytes())
        payload=zlib.compress(raster.tobytes(),1)
        stream=io.BytesIO();image=Image(stream,image_id=42,tmux=False)
        image.pixels(payload,size=raster.size);image.pixels(payload,True,size=raster.size)
        packets=stream.getvalue().split(b'\x1b_G')[1:]
        self.assertIn(b'f=24',packets[0]);self.assertIn(b'o=z',packets[0])
        self.assertIn(b's=300,v=680',packets[0])
        encoded=[]
        for packet in packets:
            header,body=packet.split(b';',1);encoded.append(body.split(b'\x1b\\')[0])
            if b'm=0' in header:break
        self.assertEqual(zlib.decompress(base64.b64decode(b''.join(encoded))),raster.tobytes())
        self.assertIn(b'a=f',stream.getvalue());self.assertIn(b'r=1,X=1',stream.getvalue())
        for packet in packets[len(encoded):]:self.assertIn(b'a=f',packet.split(b';',1)[0])

    def test_placeholders_are_normal_cells_with_truecolor_id(self):
        stream=io.BytesIO();image=Image(stream,image_id=0x123456,tmux=True)
        image.place(6,4);value=stream.getvalue()
        self.assertEqual(value.count('\U0010eeee'.encode()),24)
        self.assertIn(b'\x1b[38;2;18;52;86m',value)
        self.assertIn(b'U=1,p=1,c=6,r=4',value)
        self.assertIn(b'\x1b[4;1H',value)
        self.assertIn(b'\x1b[58;2;0;0;1m',value)
        image.placement_id=2;image.place(6,4)
        self.assertIn(b'\x1b[58;2;0;0;2m',stream.getvalue())

    def test_placement_heartbeat_does_not_repaint_cells_or_rotate_id(self):
        stream=io.BytesIO();image=Image(stream,image_id=42,tmux=False)
        image.place(6,4)
        first=stream.getvalue()
        self.assertIn(b'\x1b[?2026h',first);self.assertIn(b'\x1b[?2026l',first)
        stream.seek(0);stream.truncate()
        image.place(6,4,repaint=False)
        heartbeat=stream.getvalue()
        self.assertIn(b'a=p',heartbeat);self.assertIn(b'p=1',heartbeat)
        self.assertNotIn('\U0010eeee'.encode(),heartbeat)
        self.assertNotIn(b'a=d',heartbeat)
        self.assertEqual(image.placement_id,1)

    @unittest.skipUnless(sys.platform=='linux','keyboard uses POSIX terminal input')
    def test_original_keyboard_commands_modifiers_and_target_guard(self):
        from keyboard import Keyboard,LAYOUT,decode_command,key_boxes,send_to_shell
        from unittest.mock import patch
        from types import SimpleNamespace
        keys=[k for row in LAYOUT.values() for k in row]
        lookup=lambda cmd:next(k for k in keys if k['cmd']==cmd)
        keyboard=Keyboard()
        self.assertEqual(keyboard.press(lookup('a')),b'a')
        keyboard.press(lookup('ESCAPED|-- SHIFT: LEFT'))
        self.assertEqual(keyboard.press(lookup('a')),b'A')
        self.assertEqual(keyboard.press(lookup('a')),b'a')
        keyboard.press(lookup('ESCAPED|-- CTRL: LEFT'))
        self.assertEqual(keyboard.press(lookup('c')),b'\x03')
        self.assertEqual(decode_command('~~~CTRLSEQ1~~~OA'),'\x1bOA')
        boxes=key_boxes(900,240)
        self.assertEqual(len(boxes),len(keys))
        for x0,y0,x1,y1,key in boxes:
            self.assertTrue(0<=x0<x1<=900 and 0<=y0<y1<=240)
        with patch('keyboard.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='wrong\n')) as run:
            with self.assertRaises(RuntimeError):send_to_shell('%99','expected',b'whoami\r')
            self.assertEqual(run.call_count,1)
        with patch('keyboard.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='expected\n')) as run:
            send_to_shell('%99','expected',b'a\r')
            self.assertEqual(run.call_args.args[0],['tmux','send-keys','-t','%99','-H','61','0d'])

    @unittest.skipUnless(sys.platform=='linux','POSIX keyboard module')
    def test_keyboard_uses_browser_measured_css_geometry_and_legends(self):
        from keyboard import GEOMETRY,key_geometry,Keyboard,LAYOUT
        for state in ('normal','shift','fn'):
            self.assertEqual([len(row) for row in GEOMETRY['states'][state]],
                             [len(row) for row in LAYOUT.values()])
        width,height=GEOMETRY['canvas']
        boxes=list(key_geometry(width,height))
        q=next(b for b in boxes if b[4]['cmd']=='q')
        self.assertAlmostEqual(q[2]-q[0],q[3]-q[1],places=3)
        back=next(b for b in boxes if b[4]['name']=='BACK')
        self.assertEqual([l['text'] for l in back[5]['labels']],['BACK'])
        shifted=next(b for b in key_geometry(width,height,'shift') if b[4]['name']=='BACK')
        self.assertEqual([l['text'] for l in shifted[5]['labels']],['DELETE'])
        enter=[b for b in boxes if b[4]['cmd']=='\r']
        self.assertLess(enter[1][1],enter[0][3])  # Original CSS overlaps the two parts.
        self.assertGreater(enter[1][3],enter[0][3])
        keyboard=Keyboard();normal=keyboard.png(1066,335)
        keyboard.modifiers.add('SHIFT');shift=keyboard.png(1066,335)
        keyboard.modifiers={'FN'};fn=keyboard.png(1066,335)
        self.assertEqual(len({normal,shift,fn}),3)

    @unittest.skipUnless(sys.platform=='linux','boot uses POSIX terminal input')
    def test_boot_source_timing_and_distinct_title_keyframes(self):
        from boot import line_delay,title_frame
        self.assertEqual(line_delay(2,200),.5)
        self.assertEqual(line_delay(25,200),.4)
        self.assertEqual(line_delay(42,200),.3)
        frames=[title_frame(640,360,t).tobytes() for t in [0,.5,.8,1.05,1.13,1.18,1.7]]
        self.assertEqual(len(set(frames)),len(frames))

    def test_actual_linux_counter_deltas_and_missing_first_sample(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('EDEX_TEST_TMPDIR')) as folder:
            p=Path(folder);(p/'net').mkdir()
            (p/'stat').write_text('cpu 1 2 3 4 5 6 7 8\ncpu0 10 0 10 80 0 0 0 0\n')
            (p/'meminfo').write_text('MemTotal: 8000 kB\nMemFree: 2000 kB\nMemAvailable: 5000 kB\nActive: 3000 kB\n')
            (p/'uptime').write_text('300.0 10.0\n')
            (p/'net/dev').write_text('header\nheader\neth0: 100 0 0 0 0 0 0 0 200 0 0 0 0 0 0 0\n')
            m=Metrics(p);first=m.sample();self.assertEqual(first['cpus'],[None])
            self.assertEqual(first['network'],[None,None])
            (p/'stat').write_text('cpu0 30 0 10 160 0 0 0 0\n')
            second=m.sample();self.assertAlmostEqual(second['cpus'][0],20)
            self.assertEqual(second['memory']['MemTotal'],8000*1024)

    def test_upstream_globe_mesh_rotates_and_modules_render(self):
        data=fixture()
        self.assertNotEqual(render('globe',320,420,data,0),render('globe',320,420,data,8))
        with tempfile.TemporaryDirectory(dir=os.environ.get('EDEX_TEST_TMPDIR')) as folder:
            (Path(folder)/'example.txt').write_text('hello')
            for kind in ['cpu','memory','network','files','globe']:
                png=render(kind,320,420,data,0,folder)
                self.assertEqual(PILImage.open(io.BytesIO(png)).size,(320,420))
        from columns import render_column
        for kind in ['system','network-column']:
            intro=render_column(kind,300,680,data,0)
            steady=render_column(kind,300,680,data,5)
            self.assertNotEqual(intro,steady)
            self.assertEqual(PILImage.open(io.BytesIO(steady)).size,(300,680))

    def test_yazi_theme_rules_match_current_schema(self):
        import tomllib
        config=tomllib.loads((Path(__file__).resolve().parents[1]/'navigation/yazi/theme.toml').read_text())
        for rule in config['filetype']['rules']:
            self.assertTrue('url' in rule or 'mime' in rule)
            self.assertNotIn('name',rule)

    def test_graph_timestamps_scroll_continuously_without_sample_boundary_reset(self):
        from columns import curve_points
        box=(0,0,300,100)
        values=[20,50,80,40,60];stamps=[10,11,12,13,14]
        before=curve_points(values,stamps,14.999,box)
        after=curve_points(values,stamps,15.001,box)
        self.assertEqual(len(before),len(after))
        # Crossing an integer second moves 0.04px, never a whole sample width.
        self.assertAlmostEqual(before[0][0]-after[0][0],.04,places=5)
        self.assertEqual(before[0][1],after[0][1])

    @unittest.skipUnless(sys.platform=='linux','POSIX cross-process graphics lock')
    def test_parallel_pane_uploads_do_not_interleave(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'transfers'
            script='''import os,sys,time
from protocol import Image
class Stream:
 def __init__(self): self.file=open(sys.argv[1],'ab',buffering=0)
 def isatty(self): return True
 def write(self,b): self.file.write(b);time.sleep(.002)
 def flush(self): self.file.flush()
Image(Stream(),image_id=int(sys.argv[2]),tmux=False).pixels(bytes(range(256))*40)
'''
            env=dict(os.environ,TMUX='isolated-test',XDG_RUNTIME_DIR=folder)
            jobs=[subprocess.Popen([sys.executable,'-c',script,str(output),str(i)],env=env,
                                    cwd=Path(__file__).resolve().parents[1]) for i in [42,43]]
            for job in jobs:self.assertEqual(job.wait(timeout=10),0)
            ongoing=False;starts=0
            for packet in output.read_bytes().split(b'\x1b_G')[1:]:
                header=packet.split(b';',1)[0]
                if b'a=t' in header:
                    self.assertFalse(ongoing);ongoing=True;starts+=1
                if b'm=0' in header:ongoing=False
            self.assertEqual(starts,2);self.assertFalse(ongoing)


if __name__=='__main__':unittest.main()
