"""Optimizations must retain the original raster, including transparent modes."""
import datetime
import math
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import columns
from render import BG,MESH,font
from test_port import fixture


def original_globe(draw,width,height,elapsed):
    # Previous full-sphere projection plus public ImageDraw.polygon, retained
    # as an independent raster reference rather than a second runtime backend.
    vertices=[];indices={};faces=[]
    for tile in MESH:
        face=[]
        for vertex in tile:
            if vertex not in indices:
                indices[vertex]=len(vertices);vertices.append(vertex)
            face.append(indices[vertex])
        faces.append((face,tuple(sum(v[i] for v in tile)/len(tile) for i in range(3))))
    radius=min(width*.42,height*.19);cx=width/2;cy=height*.43
    angle=elapsed*2*math.pi/45;ct=math.cos(.630);st=math.sin(.630)
    ca=math.cos(angle);sa=math.sin(angle)
    ax=ca*radius;az=sa*radius;bx=sa*st*radius;by=ct*radius;bz=-ca*st*radius
    dx=-sa*ct;dy=st;dz=ca*ct
    projected=[(cx+x*ax+z*az,cy-(x*bx+y*by+z*bz)) for x,y,z in vertices]
    for face,(x,y,z) in faces:
        depth=x*dx+y*dy+z*dz
        if depth>0:
            draw.polygon([projected[i] for i in face],outline=columns.GLOBE_INKS[min(255,round(depth*255))])


def original_fit(value,face,available):
    if face.getlength(value)<=available:return value
    while value and face.getlength(value+'…')>available:value=value[:-1]
    return value+'…' if value else ''


class RenderOptimizationTest(unittest.TestCase):
    def test_static_surface_cache_matches_uncached_frames_and_data_changes(self):
        fixed=datetime.datetime(2026,1,1,12,34,56)
        for grid in ('0','1'):
            with patch.dict(os.environ,EDEX_GRID_BACKGROUND=grid),patch('columns.datetime.datetime') as clock:
                clock.now.return_value=fixed
                for kind in ('system','network-column'):
                    for width,height in ((180,140),(220,420),(306,600),(396,640)):
                        renderer=columns.ColumnRenderer();data=fixture()
                        data['sample_times']=list(range(80))
                        for elapsed in (0,1,3.4,4,4.04,4.5,5):
                            if elapsed==5:
                                data=dict(data,uptime=420,net_totals=[2**24,2**25])
                                data['details']=dict(address='255.255.255.255',state='UP',
                                    processes=[dict(pid=12345,name='example',cpu=12.3,memory=5.0)])
                                clock.now.return_value=fixed+datetime.timedelta(seconds=1)
                            now=81+elapsed
                            expected=columns.render_column(kind,width,height,data,elapsed,now,raster=True)
                            actual=renderer.raster(kind,width,height,data,elapsed,now)
                            self.assertEqual(expected.tobytes(),actual.tobytes(),(grid,kind,width,height,elapsed))
                            self.assertLessEqual(renderer.cache_bytes,renderer.MAX_CACHE_BYTES)

    def test_static_surface_cache_is_single_entry_bounded_and_not_returned(self):
        renderer=columns.ColumnRenderer();data=fixture()
        fixed=datetime.datetime(2026,1,1,12,34,56)
        with patch('columns.render_column',wraps=columns.render_column) as draw,patch('columns.datetime.datetime') as clock, \
                patch.dict(os.environ,EDEX_GRID_BACKGROUND='0'):
            clock.now.return_value=fixed
            first=renderer.raster('system',220,420,data,10,20)
            first.paste('red',(0,0,220,420))
            second=renderer.raster('system',220,420,data,10,20)
            self.assertEqual(draw.call_count,1)
            self.assertNotEqual(first.tobytes(),second.tobytes())
            renderer.raster('system',220,420,dict(data),10,20)
            self.assertEqual(draw.call_count,2)
            renderer.raster('system',306,600,data,10,20)
            self.assertEqual(draw.call_count,3)
            self.assertEqual(renderer.cache_bytes,306*600*3)
            with patch.dict(os.environ,EDEX_GRID_BACKGROUND='1'):
                rgba=renderer.raster('system',306,600,data,10,20)
                self.assertEqual(rgba.mode,'RGBA')
                self.assertEqual(renderer.cache_bytes,306*600*4)
                self.assertEqual(draw.call_count,4)
        with patch.object(renderer,'MAX_CACHE_BYTES',1):
            expected=columns.render_column('system',220,420,data,10,20,raster=True)
            actual=renderer.raster('system',220,420,data,10,20)
            self.assertEqual(expected.tobytes(),actual.tobytes())
            self.assertEqual(renderer.cache_bytes,0)
        self.assertIsNone(renderer._data)
        renderer.raster('network-column',220,420,data,10,20)
        self.assertEqual(renderer.cache_bytes,0)

    def test_clock_second_rebuilds_system_surface_without_replacing_sample(self):
        renderer=columns.ColumnRenderer();data=fixture()
        fixed=datetime.datetime(2026,1,1,12,34,56)
        with patch('columns.datetime.datetime') as clock,patch('columns.render_column',wraps=columns.render_column) as draw:
            clock.now.return_value=fixed
            renderer.raster('system',220,420,data,10,20)
            renderer.raster('system',220,420,data,10.04,20.04)
            self.assertEqual(draw.call_count,1)
            clock.now.return_value=clock.now.return_value+datetime.timedelta(seconds=1)
            renderer.raster('system',220,420,data,10.08,20.08)
            self.assertEqual(draw.call_count,2)

    def test_globe_matches_previous_renderer_across_angles_sizes_and_modes(self):
        for mode in ('RGB','RGBA'):
            for width,height in ((220,420),(360,640)):
                for elapsed in (0,1/24,1,7.5,22.5,44.99):
                    before=Image.new(mode,(width,height),BG if mode=='RGB' else (0,0,0,0))
                    after=before.copy()
                    original_globe(ImageDraw.Draw(before),width,height,elapsed)
                    columns.draw_globe(ImageDraw.Draw(after),width,height,elapsed)
                    self.assertEqual(before.tobytes(),after.tobytes(),(mode,width,height,elapsed))

    def test_public_fallback_handles_missing_or_changed_pillow_primitive(self):
        for mode in ('RGB','RGBA'):
            expected=Image.new(mode,(220,420));original_globe(ImageDraw.Draw(expected),220,420,10)
            public=Image.new(mode,(220,420))
            with patch('columns.native_globe_inks',return_value=None):
                columns.draw_globe(ImageDraw.Draw(public),220,420,10)
            self.assertEqual(expected.tobytes(),public.tobytes())
            changed=Image.new(mode,(220,420));draw=ImageDraw.Draw(changed)
            with patch('columns.native_globe_inks',return_value=tuple(range(256))):
                primitive=unittest.mock.Mock(side_effect=TypeError('changed signature'))
                proxy=SimpleNamespace(mode=mode,draw=SimpleNamespace(draw_polygon=primitive),polygon=draw.polygon)
                columns.draw_globe(proxy,220,420,10)
            self.assertEqual(primitive.call_count,1)
            self.assertEqual(expected.tobytes(),changed.tobytes())

    def test_cached_measurement_preserves_ellipsis_and_full_instrument_pixels(self):
        for size in (10,15,28):
            face=font(size)
            for value in ('','POWER','long-example-process-name','café 文件'):
                for width in (-1,0,12,50,150):
                    self.assertEqual(columns.fit_text(value,face,width),original_fit(value,face,width))
        fixed=datetime.datetime(2026,1,1,12,34,56)
        with patch('columns.datetime.datetime') as clock:
            clock.now.return_value=fixed
            for grid in ('0','1'):
                with patch.dict(os.environ,EDEX_GRID_BACKGROUND=grid):
                    for kind in ('system','network-column'):
                        optimized=columns.render_column(kind,260,500,fixture(),10,now=20,raster=True)
                        with patch('columns.fit_text',side_effect=original_fit), \
                             patch('columns.text_width',side_effect=lambda value,face:face.getlength(value)), \
                             patch('columns.native_globe_inks',return_value=None):
                            original=columns.render_column(kind,260,500,fixture(),10,now=20,raster=True)
                        self.assertEqual(original.tobytes(),optimized.tobytes(),(grid,kind))


if __name__=='__main__':unittest.main()
