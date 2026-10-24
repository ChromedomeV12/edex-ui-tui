"""Real Yazi navigation on disposable files in a private tmux server."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fcntl
import json
import os
from pathlib import Path
import pty
import re
import select
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]


class YaziNavigationTest(unittest.TestCase):
    def test_grid_keys_directories_mouse_filter_and_file_activation(self):
        label='edex-yazi-check-'+str(os.getpid())
        def tmux(*args):
            return subprocess.run(['tmux','-L',label,'-f',str(ROOT/'tmux.conf'),*args],check=True,
                                  capture_output=True,text=True,timeout=5).stdout.strip()
        with tempfile.TemporaryDirectory(prefix='edex-yazi-check-') as folder:
            work=Path(folder);files=work/'files';files.mkdir();(files/'00-folder').mkdir()
            for i in range(40):(files/f'{i:02d}.txt').write_text('fixture')
            (files/'.hidden.txt').write_text('hidden fixture')
            config=work/'config';shutil.copytree(ROOT/'navigation/yazi',config)
            log=work/'opened.json';opener=work/'opener.py'
            opener.write_text('import json,sys\nfrom pathlib import Path\nPath('+repr(str(log))+').write_text(json.dumps(sys.argv[1:]))\n')
            with (config/'yazi.toml').open('a') as out:
                command=shlex.join([sys.executable,str(opener)])+' %s'
                out.write('\n[opener]\ntest = [{ run = '+json.dumps(command)+', desc = "Test recorder" }]\n[open]\nrules = [{ url = "*", use = "test" }]\n')
            master,slave=pty.openpty();client=None;stop=threading.Event();thread=None
            fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',16,100,900,320))
            try:
                pane=tmux('new-session','-d','-s','edex','-x','100','-y','16','-P','-F','#{pane_id}',
                          'env','YAZI_CONFIG_HOME='+str(config),'yazi',str(files))
                tmux('set-option','-p','-t',pane,'allow-passthrough','off')
                client=subprocess.Popen(['tmux','-L',label,'attach','-t','edex'],stdin=slave,stdout=slave,stderr=slave,
                                        env=dict(os.environ,TERM='xterm-kitty',LANG='C.UTF-8'))
                def drain():
                    while not stop.is_set():
                        if select.select([master],[],[],.05)[0]:
                            try:os.read(master,65536)
                            except OSError:return
                thread=threading.Thread(target=drain,daemon=True);thread.start()
                def screen():return tmux('capture-pane','-p','-t',pane)
                def wait(predicate):
                    deadline=time.monotonic()+4;last=''
                    while time.monotonic()<deadline:
                        last=screen()
                        if predicate(last):return last
                        time.sleep(.04)
                    self.fail('Yazi did not reach expected state:\n'+last)
                def position(number,total=42):
                    return wait(lambda s:bool(re.search(r'\b'+str(number)+r' / '+str(total)+r'\s*$',s)))
                def key(*keys):tmux('send-keys','-t',pane,*keys)
                initial=position(1);self.assertIn('00-folder',initial.splitlines()[-1])
                key('Down');position(8)
                key('Right');position(9)
                key('Left');position(8)
                key('Up');position(1)
                key('j');position(8)
                key('k');position(1)
                key('PageDown');position(15)
                key('PageUp');position(1)
                key('End');position(42)
                key('Home');position(1)
                key('Enter')
                empty=position(0,0);self.assertIn('00-folder',empty.splitlines()[0])
                self.assertIn('Root /',empty);self.assertIn('Go up',empty)
                self.assertFalse(log.exists(),'Entering a directory must not invoke the file opener')
                os.write(master,b'\x1b[<0;22;3M\x1b[<0;22;3m');position(1)
                key('Enter');position(0,0)
                key('BSpace');position(1)
                # Mouse click at row zero, third card: file index zero.
                # Then click fourth card: file index one. Neither opens anything.
                for x,pos in [(36,1),(50,2)]:
                    os.write(master,f'\x1b[<0;{x};3M\x1b[<0;{x};3m'.encode());position(pos)
                self.assertFalse(log.exists(),'A click must only highlight, never open')
                key('Enter');deadline=time.monotonic()+3
                while not log.exists() and time.monotonic()<deadline:time.sleep(.03)
                self.assertTrue(log.exists(),'Enter did not invoke file opener')
                opened=json.loads(log.read_text());self.assertEqual(len(opened),1)
                self.assertTrue(Path(opened[0]).is_file())
                key('Space');position(3);self.assertIn('* ',screen())
                key('Escape');time.sleep(.1)
                key('f');key('z','z','z','n','o','m','a','t','c','h','Enter')
                filtered=position(0,0);self.assertIn('No filter results',filtered)
                key('Escape');wait(lambda s:'42 items' in s)
                key('Home');position(1)
                os.write(master,b'\x1b[<65;36;3M')
                wheeled=wait(lambda s:bool(re.search(r'\b([2-9]|[1-4][0-9]) / 42\s*$',s)))
                number=int(re.search(r'(\d+) / 42\s*$',wheeled)[1]);self.assertEqual((number-1)%7,0)
                os.write(master,b'\x1b[<64;36;3M');position(1)
                tmux('set-window-option','-t','edex','window-size','manual')
                tmux('resize-window','-t','edex','-x','80','-y','14');time.sleep(.2)
                key('Down');position(7)
                self.assertEqual(tmux('display-message','-p','-t',pane,'#{pane_dead}'),'0')
            finally:
                stop.set();subprocess.run(['tmux','-L',label,'kill-server'],capture_output=True)
                if client:
                    try:client.wait(timeout=2)
                    except subprocess.TimeoutExpired:client.kill();client.wait()
                if thread:thread.join(timeout=1)
                os.close(master);os.close(slave)


if __name__=='__main__':unittest.main()
