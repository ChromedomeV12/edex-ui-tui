"""Real tmux resize contracts on a private server; no interactive input."""
import os
import secrets
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from layout import reflow

ROOT=Path(__file__).resolve().parents[1]


class LayoutTest(unittest.TestCase):
    def setUp(self):
        self.socket='edex-layout-check-'+str(os.getpid())+'-'+secrets.token_hex(4)
        self.calls=[]
        self.shell=self.run_tmux('new-session','-d','-s','edex','-x','209','-y','49','-P','-F','#{pane_id}','sleep','120')
        def split(target,*flags):
            return self.run_tmux('split-window','-d','-t',target,*flags,'-P','-F','#{pane_id}','sleep','120')
        self.files=split(self.shell,'-f','-v','-l','30%')
        self.run_tmux('select-pane','-t',self.files,'-T','Files: example | directory')
        self.system=split(self.shell,'-h','-b','-l','17%')
        self.network=split(self.shell,'-h','-l','20%')
        self.tabs=split(self.shell,'-v','-b','-l','2')
        self.padding=split(self.shell,'-v','-l','1')
        self.keyboard=self.run_tmux('new-window','-d','-t','edex','-n','_keyboard','-P','-F','#{pane_id}','sleep','120')
        for pane,title in ((self.system,'System'),(self.network,'Network-column'),(self.keyboard,'Keyboard')):
            self.run_tmux('select-pane','-t',pane,'-T',title)
        for name,pane in (('shell',self.shell),('files',self.files),('tabs',self.tabs),('shell-padding',self.padding)):
            self.run_tmux('set-option','-t','edex','@edex-'+name,pane)
        self.run_tmux('join-pane','-d','-s',self.keyboard,'-t',self.files,'-h','-l','62%')
        self.pids={pane:self.value(pane,'pane_pid') for pane in
                   (self.shell,self.files,self.system,self.network,self.tabs,self.padding,self.keyboard)}

    def tearDown(self):
        subprocess.run(['tmux','-L',self.socket,'kill-server'],capture_output=True)

    def run_tmux(self,*args):
        self.calls.append(args)
        return subprocess.run(['tmux','-L',self.socket,'-f',str(ROOT/'tmux.conf'),*args],
                              check=True,capture_output=True,text=True,timeout=5).stdout.strip()

    def value(self,pane,field):
        return self.run_tmux('display-message','-p','-t',pane,'#{'+field+'}')

    def test_shrink_grow_and_noop_preserve_processes_and_proportions(self):
        for width,height in ((160,40),(209,49),(140,40),(130,42),(120,40),(240,60)):
            self.run_tmux('resize-window','-t','edex:0','-x',str(width),'-y',str(height))
            reflow(self.run_tmux)
            for pane in (self.system,self.network):
                self.assertEqual(int(self.value(pane,'pane_width')),int(width*.17))
            self.assertEqual(int(self.value(self.keyboard,'pane_width')),int(width*.62))
            self.assertEqual(int(self.value(self.files,'pane_height')),int(height*.36))
            self.assertEqual(self.value(self.tabs,'pane_height'),'2')
            self.assertEqual(self.value(self.padding,'pane_height'),'1')
            self.calls.clear()
            self.assertFalse(reflow(self.run_tmux))
            self.assertFalse(any(call[0] in ('resize-pane','set-option') for call in self.calls))
        for pane,pid in self.pids.items():self.assertEqual(self.value(pane,'pane_pid'),pid)

    def test_hidden_keyboard_and_zoom_do_not_change_input_or_pane_lifecycle(self):
        self.run_tmux('break-pane','-d','-s',self.keyboard,'-n','_keyboard')
        reflow(self.run_tmux)
        self.assertEqual(self.value(self.files,'pane_height'),'14')
        self.assertEqual(self.value(self.keyboard,'pane_pid'),self.pids[self.keyboard])
        self.run_tmux('resize-pane','-Z','-t',self.shell)
        self.calls.clear()
        self.assertFalse(reflow(self.run_tmux))
        self.assertFalse(any(call[0]=='resize-pane' for call in self.calls))
        self.assertEqual(self.value(self.shell,'window_zoomed_flag'),'1')
        self.assertEqual(self.value(self.shell,'pane_pid'),self.pids[self.shell])


if __name__=='__main__':unittest.main()
