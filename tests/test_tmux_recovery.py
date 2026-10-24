"""Linux integration check: a real renderer survives a delayed tmux reply.

Uses a private temporary tmux server and a drained PTY, not the user's session.
This checks lifecycle/recovery, not visual rendering in Kitty.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fcntl
import os
from pathlib import Path
import pty
import select
import shutil
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]


class RecoveryTest(unittest.TestCase):
    def test_renderer_recovers_after_real_control_query_timeout(self):
        real_tmux=shutil.which('tmux')
        self.assertIsNotNone(real_tmux)
        with tempfile.TemporaryDirectory(prefix='edex-control-check-') as folder:
            work=Path(folder);shim=work/'tmux';marker=work/'delayed'
            shim.write_text('#!'+sys.executable+'\n'+
                'import os,sys,time\nfrom pathlib import Path\n'+
                f'marker=Path({str(marker)!r})\n'+
                "if 'display-message' in sys.argv and not marker.exists():\n"+
                " marker.write_text('reply deliberately delayed beyond query timeout')\n"+
                ' time.sleep(1.5)\n'+
                f'os.execv({real_tmux!r},[{real_tmux!r},*sys.argv[1:]])\n')
            shim.chmod(0o755)
            label='edex-control-check-'+str(os.getpid())
            def tmux(*args,check=True):
                return subprocess.run([real_tmux,'-L',label,'-f',str(ROOT/'tmux.conf'),*args],
                                      capture_output=True,text=True,check=check,timeout=5)
            master,slave=pty.openpty();client=None
            fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,140,1260,720))
            try:
                tmux('new-session','-d','-s','check','-x','140','-y','40',
                     'env','PATH='+folder+os.pathsep+os.environ['PATH'],
                     sys.executable,str(ROOT/'panel.py'),'system','--fps','2')
                tmux('set-option','-g','remain-on-exit','on')
                client=subprocess.Popen([real_tmux,'-L',label,'attach','-t','check'],
                                        stdin=slave,stdout=slave,stderr=slave,
                                        env=dict(os.environ,TERM='xterm-kitty'))
                captured=bytearray();deadline=time.monotonic()+4
                while time.monotonic()<deadline:
                    if select.select([master],[],[],.1)[0]:
                        try:captured.extend(os.read(master,65536))
                        except OSError:break
                self.assertTrue(marker.exists(),'The slow-reply fault was not exercised')
                self.assertEqual(tmux('display-message','-p','-t','check','#{pane_dead}').stdout.strip(),'0')
                self.assertIn(b'a=t',captured,'Renderer did not recover and upload its first image')
                self.assertIn(b'a=f',captured,'Renderer did not continue producing animation frames')
                self.assertGreaterEqual(captured.count(b'a=p'),2,'Placement was not reasserted after startup')
                self.assertEqual(captured.count(b'a=t'),1,'Placement recovery must not reload the root texture')
            finally:
                tmux('kill-server',check=False)
                if client is not None:
                    try:client.wait(timeout=3)
                    except subprocess.TimeoutExpired:client.kill();client.wait()
                os.close(master);os.close(slave)


if __name__=='__main__':unittest.main()
