"""Ubuntu binary-package checks; run where dpkg-deb is installed."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('edex_debian',ROOT/'packaging/debian/build.py')
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class DebianPackageTest(unittest.TestCase):
    def test_binary_metadata_ownership_contents_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            packages=[builder.build(folder/name,'Package Test <test@example.invalid>',epoch=1792972800)
                      for name in ('first','second')]
            self.assertEqual(hashlib.sha256(packages[0].read_bytes()).digest(),
                             hashlib.sha256(packages[1].read_bytes()).digest())
            metadata=subprocess.check_output(['dpkg-deb','--field',str(packages[0])],text=True)
            self.assertIn('Architecture: all',metadata)
            self.assertIn('python3-pil (>= 10.2)',metadata)
            self.assertIn('Suggests: yazi',metadata)
            self.assertEqual(subprocess.run(['dpkg','--compare-versions','0.1.0~alpha1-1','lt','0.1.0'],check=False).returncode,0)
            data=subprocess.check_output(['dpkg-deb','--fsys-tarfile',str(packages[0])])
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                members=archive.getmembers()
                names={m.name.removeprefix('./') for m in members}
                self.assertTrue(all(m.uid==0 and m.gid==0 for m in members))
                self.assertTrue(all(m.mode==0o755 for m in members if m.isdir()))
                self.assertFalse(any(name.startswith(('etc/','home/')) or '/__pycache__/' in name for name in names))
                self.assertIn('usr/share/doc/edex-ui-tui/copyright',names)
                self.assertIn('usr/share/man/man1/edex-ui-tui.1.gz',names)
                self.assertIn('usr/share/doc/edex-ui-tui/licenses/OFL.txt',names)
                self.assertFalse(any(name.startswith('usr/share/licenses/') for name in names))
            installed=folder/'extracted'
            subprocess.run(['dpkg-deb','--extract',str(packages[0]),str(installed)],check=True)
            wrapper=(installed/'usr/bin/edex-ui-tui').read_text()
            self.assertIn('/usr/bin/python3 ',wrapper)
            self.assertEqual((installed/'usr/bin/edex-ui-tui').stat().st_mode&0o777,0o755)
            runtime=installed/'usr/share/edex-ui-tui'
            manifest=json.loads((runtime/'UPSTREAM.json').read_text())
            for row in manifest['files']+[r for r in manifest['derived_assets'] if 'sha256' in r]:
                path=row.get('local_path',row.get('path'))
                self.assertEqual(hashlib.sha256((runtime/path).read_bytes()).hexdigest(),row['sha256'])
            for row in json.loads((runtime/'assets/fonts/SOURCE.json').read_text())['files']:
                self.assertEqual(hashlib.sha256((runtime/'assets/fonts'/row['path']).read_bytes()).hexdigest(),row['sha256'])
            subprocess.run([sys.executable,'-I','-c','import sys;sys.path.insert(0,".");import app,keyboard,columns,render;assert render.font(16).getbbox("eDEX")'],
                           cwd=runtime,check=True,capture_output=True,text=True)
            control=subprocess.check_output(['dpkg-deb','--ctrl-tarfile',str(packages[0])])
            with tarfile.open(fileobj=io.BytesIO(control)) as archive:
                self.assertFalse(any(m.name.removeprefix('./') in ('preinst','postinst','prerm','postrm','conffiles') for m in archive.getmembers()))

    def test_reject_control_field_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                builder.build(directory,'Package Test <test@example.invalid>\nDepends: injected')


if __name__=='__main__':unittest.main()
