"""Real tmux shell swapping on a private test server, never the live demo."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import workspaces


class WorkspacesTest(unittest.TestCase):
    def test_switch_preserves_shell_process_and_other_sections(self):
        binary=shutil.which('tmux');self.assertIsNotNone(binary)
        label='edex-workspace-check-'+str(os.getpid())
        def tmux(*args):
            return subprocess.run([binary,'-L',label,'-f',str(workspaces.ROOT/'tmux.conf'),*args],check=True,capture_output=True,
                                  text=True,timeout=5).stdout.strip()
        with tempfile.TemporaryDirectory() as folder,patch('workspaces.tmux',side_effect=tmux):
            try:
                shell=tmux('new-session','-d','-s','edex','-c',folder,'-x','180','-y','50','-P','-F','#{pane_id}',
                           'bash','--noprofile','--norc')
                tmux('set-option','-t','edex','@edex-shell',shell)
                tmux('set-option','-p','-t',shell,'@edex-input-token','integration-test-token')
                files=tmux('split-window','-d','-t',shell,'-v','-P','-F','#{pane_id}','sleep','30')
                pid=tmux('display-message','-p','-t',shell,'#{pane_pid}')
                workspaces.install()
                header=workspaces.option('@edex-tabs')
                workspaces.switch(2)
                second=workspaces.option('@edex-shell')
                self.assertNotEqual(second,shell)
                self.assertEqual(workspaces.option('@edex-active-slot'),'2')
                self.assertEqual(tmux('show-options','-p','-v','-t',second,'@edex-input-token'),'integration-test-token')
                workspaces.switch(1)
                self.assertEqual(workspaces.option('@edex-shell'),shell)
                self.assertEqual(tmux('display-message','-p','-t',shell,'#{pane_pid}'),pid)
                self.assertEqual(tmux('display-message','-p','-t',shell,'#{pane_current_path}'),folder)
                for pane in [files,header]:
                    self.assertEqual(tmux('display-message','-p','-t',pane,'#{pane_dead}'),'0')
                with self.assertRaises(ValueError):workspaces.switch(6)
            finally:
                subprocess.run([binary,'-L',label,'kill-server'],capture_output=True)


if __name__=='__main__':unittest.main()
