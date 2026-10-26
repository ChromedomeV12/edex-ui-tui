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
    def test_column_text_keeps_addresses_and_separates_values_on_resize(self):
        import columns
        from unittest.mock import patch
        original_stamp=columns.text_stamp;original_paste=PILImage.Image.paste
        data=fixture()
        data['details']=dict(address='255.255.255.255',state='UP',interface='enp0s31f6',
            processes=[dict(pid=1234567,name='example-long-process-name',cpu=1600.0,memory=100.0)])
        for width,height in ((350,680),(260,500),(220,420)):
            records={}
            def stamp(value,face,ink):
                art=original_stamp(value,face,ink).copy();art.info['audit_value']=value
                return art
            def paste(image,art,box=None,mask=None):
                if isinstance(art,PILImage.Image) and 'audit_value' in art.info:
                    bounds=art.getbbox()
                    if bounds:
                        x,y=box;records.setdefault(art.info['audit_value'],[]).append(
                            (x+bounds[0],y+bounds[1],x+bounds[2],y+bounds[3]))
                return original_paste(image,art,box,mask)
            with patch('columns.text_stamp',side_effect=stamp),patch.object(PILImage.Image,'paste',new=paste):
                columns.render_column('network-column',width,height,data,10,now=20)
                self.assertIn(data['details']['address'],records)
                columns.render_column('system',width,height,data,10,now=20)
            cpu=records['1600.0%'][0];memory=records['100.0%'][0]
            self.assertLess(cpu[2],memory[0])
            self.assertLess(memory[2],width)
            self.assertLessEqual(records['UPTIME'][0][3],records['0:05'][0][1])

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
        continuing=False
        for chunk in chunks:
            self.assertLess(len(chunk),2200)
            header=chunk.split(b';',1)[0].split(b'\x1b\\',1)[0]
            fields=dict(field.split(b'=',1) for field in header.split(b','))
            if continuing:
                allowed={b'm',b'a',b'q'} if fields.get(b'a')==b'f' else {b'm',b'q'}
                self.assertTrue(set(fields)<=allowed,header)
            continuing=fields.get(b'm')==b'1'
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

    @unittest.skipUnless(sys.platform=='linux','POSIX keyboard module')
    def test_arrow_alignment_and_hit_regions_at_multiple_sizes(self):
        from keyboard import key_geometry
        for state in ('normal','shift','fn'):
            for width,height in ((1066,335),(1152,320),(810,260),(540,220)):
                arrows={b[4]['name'].rsplit('_',1)[-1]:b
                        for b in key_geometry(width,height,state) if 'ICON: ARROW_' in b[4]['name']}
                up,down=arrows['UP'],arrows['DOWN']
                self.assertAlmostEqual(up[0]+up[2],down[0]+down[2])
                for b in arrows.values():
                    x,y,w,h=b[5]['rect'];ix,iy,iw,ih=b[5]['icon_rect']
                    self.assertAlmostEqual(x+w/2,ix+iw/2)
                    self.assertAlmostEqual(y+h/2,iy+ih/2)
                    self.assertTrue(0<=b[0]<b[2]<=width)
                    self.assertTrue(0<=b[1]<b[3]<=height)
                self.assertAlmostEqual(arrows['LEFT'][1],down[1])
                self.assertAlmostEqual(arrows['RIGHT'][1],down[1])

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


class BorderFrameTests(unittest.TestCase):
    def _alpha(self,image):
        return image.getchannel('A')

    def _components(self,image):
        # 8-connected components of the alpha>=8 pixels; the threshold
        # ignores insignificant anti-aliasing tails
        buf=self._alpha(image).tobytes();w,h=image.size
        total=[i for i in range(w*h) if buf[i]>=8]
        if not total:return 0,0
        seen={total[0]};frontier=[total[0]]
        while frontier:
            y,x=divmod(frontier.pop(),w)
            for ny in range(y-1 if y else 0,min(y+2,h)):
                for nx in range(x-1 if x else 0,min(x+2,w)):
                    j=ny*w+nx
                    if buf[j]>=8 and j not in seen:
                        seen.add(j);frontier.append(j)
        return len(seen),len(total)

    def _corners(self,image,height):
        # top-right and bottom-left are 15px clipped: the bbox corner cells stay
        # transparent and a diagonal joins the two bars; top-left and bottom-right
        # are square, so the contour reaches those bbox corners
        s=max(1,int(height*0.0018+0.5))  # 0.18vh stroke convention
        a=self._alpha(image);l,t,r,b=a.getbbox()
        self.assertGreater(a.getpixel((l,t)),0)
        self.assertGreater(a.getpixel((r-1,b-1)),0)
        self.assertEqual(a.getpixel((r-1,t)),0)
        self.assertEqual(a.getpixel((l,b-1)),0)
        tr=[(x,y)for y in range(t,t+16)for x in range(r-16,r)if a.getpixel((x,y))]
        self.assertTrue(any(x<r-s and y>t+s for x,y in tr))
        bl=[(x,y)for y in range(b-16,b)for x in range(l,l+16)if a.getpixel((x,y))]
        self.assertTrue(any(x>l+s and y<b-s for x,y in bl))

    def test_frame_is_closed_contour_on_normal_viewport(self):
        from border_frame import render_frame
        image=render_frame(1800,1000,(20,80,1780,920))
        self.assertEqual((image.size,image.mode),((1800,1000),'RGBA'))
        # shell interior stays fully transparent
        self.assertIsNone(image.crop((20,80,1780,920)).getchannel('A').getbbox())
        reached,total=self._components(image)
        self.assertEqual(reached,total)
        self._corners(image,1000)

    def test_frame_keeps_shell_clear_on_tight_viewport(self):
        from border_frame import render_frame
        image=render_frame(300,1000,(30,10,270,990))
        self.assertEqual((image.size,image.mode),((300,1000),'RGBA'))
        self.assertIsNone(image.crop((30,10,270,990)).getchannel('A').getbbox())
        reached,total=self._components(image)
        self.assertEqual(reached,total)
        self._corners(image,1000)

    def test_frame_clamps_into_small_gutters_without_covering_shell(self):
        from border_frame import render_frame
        image=render_frame(200,1000,(2,1,199,999))
        self.assertEqual((image.size,image.mode),((200,1000),'RGBA'))
        a=self._alpha(image)
        self.assertIsNone(image.crop((2,1,199,999)).getchannel('A').getbbox())
        # the canvas is the viewport, so any stroke is within it; the frame
        # must still be drawn when gutters are narrower than the stroke
        self.assertIsNotNone(a.getbbox())
        reached,total=self._components(image)
        self.assertEqual(reached,total)
        # every gutter zero: no frame at all
        empty=render_frame(200,1000,(0,0,200,1000))
        self.assertIsNone(empty.getchannel('A').getbbox())

if __name__=='__main__':unittest.main()
