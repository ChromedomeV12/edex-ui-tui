"""Native popup lifecycle and input isolation on a disposable tmux server."""
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import fcntl
import termios
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


class PopupTest(unittest.TestCase):
    def test_onscreen_input_is_blocked_when_modal_owns_focus(self):
        import keyboard
        from types import SimpleNamespace
        with patch('keyboard.query',return_value='1'),patch('keyboard.send_to_shell') as send:
            keyboard.route_key(SimpleNamespace(token='test'),b'never execute')
            send.assert_not_called()

    def test_close_reopen_preserves_shell_and_clears_input_guard(self):
        socket='edex-popup-test-'+str(os.getpid())
        def tm(*args):
            return subprocess.check_output(['tmux','-L',socket,'-f',str(ROOT/'tmux.conf'),*args],text=True).strip()
        def wait_for(predicate):
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                if predicate():return
                time.sleep(.05)
            self.fail('Popup lifecycle timed out')
        with tempfile.TemporaryDirectory(prefix='edex-popup-') as folder:
            master,slave=pty.openpty();client=None;stop=threading.Event();drainer=None
            fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',50,160,1440,1000))
            env=dict(os.environ,EDEX_TMUX_SOCKET=socket,TERM='xterm-kitty',LANG='C.UTF-8')
            try:
                shell=tm('new-session','-d','-s','edex','-x','160','-y','50','-c',folder,
                         '-P','-F','#{pane_id}','sleep','60')
                tm('set-option','-t','edex','@edex-shell',shell)
                identity=tm('display-message','-p','-t',shell,'#{pane_pid}|#{pane_current_path}')
                origin=tm('split-window','-d','-h','-t',shell,'-P','-F','#{pane_id}','sleep','60')
                tm('select-pane','-t',origin)
                client=subprocess.Popen(['tmux','-L',socket,'attach','-t','edex'],stdin=slave,stdout=slave,stderr=slave,env=env)
                def drain():
                    while not stop.is_set():
                        if select.select([master],[],[],.05)[0]:
                            try:os.read(master,65536)
                            except OSError:return
                drainer=threading.Thread(target=drain);drainer.start()
                wait_for(lambda:tm('display-message','-p','-t',shell,'#{session_attached}')=='1')
                for _ in range(2):
                    controller=subprocess.Popen([sys.executable,str(ROOT/'popups.py')],env=env,
                                                stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                    try:
                        wait_for(lambda:tm('show-options','-qv','-t','edex','@edex-modal-open')=='1')
                        time.sleep(.15)
                        self.assertIsNone(controller.poll())
                        duplicate=subprocess.run([sys.executable,str(ROOT/'popups.py')],env=env,timeout=2,capture_output=True)
                        self.assertEqual(duplicate.returncode,0,duplicate.stderr)
                        tm('display-popup','-C','-t',shell)
                        _,error=controller.communicate(timeout=5)
                        self.assertEqual(controller.returncode,0,error)
                        self.assertEqual(tm('show-options','-qv','-t','edex','@edex-modal-open'),'0')
                        self.assertEqual(tm('display-message','-p','-t',shell,'#{pane_pid}|#{pane_current_path}'),identity)
                        self.assertEqual(tm('display-message','-p','#{pane_id}'),origin)
                    finally:
                        if controller.poll() is None:controller.terminate();controller.communicate(timeout=5)
            finally:
                stop.set()
                subprocess.run(['tmux','-L',socket,'kill-server'],capture_output=True)
                if client:
                    try:client.wait(timeout=2)
                    except subprocess.TimeoutExpired:client.kill();client.wait()
                if drainer:drainer.join(timeout=1)
                os.close(master);os.close(slave)


if __name__=='__main__':unittest.main()
