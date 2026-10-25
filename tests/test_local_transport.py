"""Local Kitty transfer files stay private, bounded and owned by one image."""
import base64
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from protocol import Image


class LocalTransportTest(unittest.TestCase):
    def test_one_packet_per_frame_and_scoped_cleanup(self):
        with patch.dict(os.environ,EDEX_GRAPHICS_TRANSPORT='tempfile'):
            stream=io.BytesIO();image=Image(stream,image_id=42,tmux=False)
            payload=bytes(range(256))*80
            image.pixels(payload,size=(80,64),channels=4)
            image.pixels(payload,update=True,size=(80,64),channels=4)
            packets=stream.getvalue().split(b'\x1b_G')[1:]
            self.assertEqual(len(packets),2)
            self.assertIn(b'a=f,t=t,f=32,i=42,q=2,s=80,v=64,o=z,r=1,X=1',packets[1])
            paths=[Path(os.fsdecode(base64.b64decode(p.split(b';')[1].split(b'\x1b')[0]))) for p in packets]
            for path in paths:
                self.assertEqual(path.read_bytes(),payload)
                if sys.platform=='linux':self.assertEqual(path.stat().st_mode&0o777,0o600)
            with tempfile.NamedTemporaryFile() as unrelated:
                image.close()
                self.assertTrue(Path(unrelated.name).exists())
            self.assertTrue(all(not p.exists() for p in paths))
            self.assertFalse(image.pending_files)

    def test_terminal_removed_files_do_not_accumulate(self):
        with patch.dict(os.environ,EDEX_GRAPHICS_TRANSPORT='tempfile'):
            image=Image(io.BytesIO(),image_id=42,tmux=False)
            try:
                for _ in range(140):
                    image.pixels(b'test')
                    self.assertEqual(len(image.pending_files),1)
                    next(iter(image.pending_files)).unlink()
            finally:image.close()

    def test_stalled_consumer_has_a_bounded_backlog(self):
        with patch.dict(os.environ,EDEX_GRAPHICS_TRANSPORT='tempfile'):
            image=Image(io.BytesIO(),image_id=42,tmux=False)
            paths=[]
            try:
                for _ in range(128):image.pixels(b'test')
                paths=list(image.pending_files)
                with self.assertRaisesRegex(RuntimeError,'backlog'):
                    image.pixels(b'not written')
                self.assertEqual(len(image.pending_files),128)
            finally:image.close()
            self.assertTrue(all(not p.exists() for p in paths))


if __name__=='__main__':unittest.main()
