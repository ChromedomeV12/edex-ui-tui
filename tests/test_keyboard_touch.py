"""Synthetic tap test through a real private tmux client; never types into a shell.

This validates the SGR mouse-emulation path, not physical touchscreen hardware.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fcntl
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
import unittest
from keyboard import key_boxes

ROOT=Path(__file__).resolve().parents[1]


class TouchPathTest(unittest.TestCase):
    def test_manual_probe_records_without_execution_and_restores_terminal(self):
        master,slave=pty.openpty();old=termios.tcgetattr(slave);child=None
        try:
            child=subprocess.Popen([sys.executable,str(ROOT/'keyboard_input_probe.py')],stdin=slave,stdout=slave,stderr=slave)
            output=bytearray();deadline=time.monotonic()+3
            while b'Ctrl-D exits' not in output and time.monotonic()<deadline:
                if select.select([master],[],[],.05)[0]:output.extend(os.read(master,65536))
            self.assertIn(b'Ctrl-D exits',output)
            time.sleep(.05);os.write(master,b'a\r')
            deadline=time.monotonic()+2
            while b"b'a\\r'" not in output and time.monotonic()<deadline:
                if select.select([master],[],[],.05)[0]:output.extend(os.read(master,65536))
            self.assertIn(b"b'a\\r'",output)
            os.write(master,b'\x04');self.assertEqual(child.wait(timeout=2),0)
            self.assertEqual(termios.tcgetattr(slave),old)
        finally:
            if child and child.poll() is None:child.kill();child.wait()
            os.close(master);os.close(slave)

    def test_client_taps_reach_only_a_raw_byte_recorder(self):
        label='edex-touch-check-'+str(os.getpid())
        def tmux(*args):
            return subprocess.run(['tmux','-L',label,'-f',str(ROOT/'tmux.conf'),*args],
                                  check=True,capture_output=True,text=True,timeout=5).stdout.strip()
        with tempfile.TemporaryDirectory(prefix='edex-touch-check-') as folder:
            folder=Path(folder);record=folder/'bytes';receiver=folder/'receiver.py'
            receiver.write_text('import os,sys,tty\ntty.setraw(0)\nwith open(sys.argv[1],"ab",buffering=0) as out:\n while True:\n  b=os.read(0,4096)\n  if not b:break\n  out.write(b)\n')
            master,slave=pty.openpty();client=None;stop=threading.Event();drainer=None
            fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',50,160,1440,1000))
            try:
                target=tmux('new-session','-d','-s','edex','-x','160','-y','50','-P','-F','#{pane_id}',
                            sys.executable,str(receiver),str(record))
                tmux('set-option','-t','edex','@edex-shell',target)
                tmux('set-option','-p','-t',target,'@edex-input-token','test-only-marker')
                keyboard=tmux('split-window','-d','-v','-l','35%','-t',target,'-P','-F','#{pane_id}',
                              sys.executable,str(ROOT/'keyboard.py'),'--shell-pane',target,'--token','test-only-marker')
                client=subprocess.Popen(['tmux','-L',label,'attach','-t','edex'],stdin=slave,stdout=slave,stderr=slave,
                                        env=dict(os.environ,TERM='xterm-kitty',LANG='C.UTF-8'))
                def drain():
                    while not stop.is_set():
                        if select.select([master],[],[],.05)[0]:
                            try:os.read(master,65536)
                            except OSError:return
                drainer=threading.Thread(target=drain,daemon=True);drainer.start()
                time.sleep(1.5)
                cols,rows,cw,ch,left,top=map(int,tmux('display-message','-p','-t',keyboard,
                    '#{pane_width},#{pane_height},#{client_cell_width},#{client_cell_height},#{pane_left},#{pane_top}').split(','))
                cw=cw or 8;ch=ch or 16;width=(cols-1)*cw;height=(rows-1)*ch
                expected=b''
                def read():return record.read_bytes() if record.exists() else b''
                def tap(command,state='normal',emitted=b''):
                    nonlocal expected
                    box=next(b for b in key_boxes(width,height,state) if b[4]['cmd']==command)
                    x=left+int((box[0]+box[2])/2/cw)+1;y=top+int((box[1]+box[3])/2/ch)+1
                    # These enter at the client PTY, exercising tmux hit routing.
                    os.write(master,f'\x1b[<0;{x};{y}M\x1b[<0;{x};{y}m'.encode())
                    expected+=emitted;deadline=time.monotonic()+2
                    if not emitted:time.sleep(.1)
                    while read()!=expected and time.monotonic()<deadline:time.sleep(.02)
                    self.assertEqual(read(),expected)
                tap('a',emitted=b'a')
                tap('ESCAPED|-- SHIFT: LEFT')
                tap('a',state='shift',emitted=b'A')
                tap(' ',emitted=b' ')
                tap('\b',emitted=b'\b')
                tap('\r',emitted=b'\r')
                for code in ('A','B','C','D'):tap('~~~CTRLSEQ1~~~O'+code,emitted=('\x1bO'+code).encode())
                tap('ESCAPED|-- CTRL: LEFT')
                tap('c',emitted=b'\x03')
                before=read()
                os.write(master,f'\x1b[<2;{left+2};{top+2}M\x1b[<2;{left+2};{top+2}m'.encode())
                time.sleep(.2);self.assertEqual(read(),before)
                self.assertEqual(tmux('display-message','-p','-t',target,'#{pane_dead}'),'0')
            finally:
                stop.set()
                subprocess.run(['tmux','-L',label,'kill-server'],capture_output=True)
                if client:
                    try:client.wait(timeout=2)
                    except subprocess.TimeoutExpired:client.kill();client.wait()
                if drainer:drainer.join(timeout=1)
                os.close(master);os.close(slave)


if __name__=='__main__':unittest.main()
