"""Real tmux shell swapping and EDEX_TMUX_SOCKET isolation on private test servers, never the live demo."""
import contextlib
import fcntl
import os
import pty
import select
import shutil
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import workspaces


class WorkspacesTest(unittest.TestCase):
    def test_launcher_passes_opt_in_animation_rate_to_both_instruments(self):
        socket='edex-rate-check-'+str(os.getpid())
        binary=shutil.which('tmux');self.assertIsNotNone(binary)
        try:
            with tempfile.TemporaryDirectory() as folder:
                full_launch(binary,socket,Path(folder),Path(folder),fps=48)
                rows=tmux_client(binary,socket,'list-panes','-t','edex:0','-F',
                                 '#{pane_title}|#{pane_start_command}').stdout.splitlines()
                instruments=[line for line in rows if line.startswith(('System|','Network-column|'))]
                self.assertEqual(len(instruments),2)
                for line in instruments:self.assertIn('--fps 48',line)
        finally:
            subprocess.run([binary,'-L',socket,'kill-server'],capture_output=True)

    def test_keyboard_resize_preserves_tabs_shell_and_hidden_worker(self):
        import launch
        label='edex-keyboard-layout-check-'+str(os.getpid())
        def tmux(*args):
            return subprocess.run(['tmux','-L',label,'-f',str(ROOT/'tmux.conf'),*args],
                                  check=True,capture_output=True,text=True,timeout=5).stdout.strip()
        try:
            shell=tmux('new-session','-d','-s','edex','-x','209','-y','49','-P','-F','#{pane_id}','sleep','30')
            files=tmux('split-window','-d','-f','-v','-t',shell,'-l','30%','-P','-F','#{pane_id}','sleep','30')
            tabs=tmux('split-window','-d','-v','-b','-t',shell,'-l','3','-P','-F','#{pane_id}','sleep','30')
            keyboard=tmux('new-window','-d','-t','edex','-n','_keyboard','-P','-F','#{pane_id}','sleep','30')
            tmux('select-pane','-t',keyboard,'-T','Keyboard')
            for option,pane in (('@edex-shell',shell),('@edex-files',files),('@edex-tabs',tabs)):
                tmux('set-option','-t','edex',option,pane)
            tmux('set-option','-p','-t',shell,'@edex-input-token','test-only-marker')
            def value(pane,field):return tmux('display-message','-p','-t',pane,'#{'+field+'}')
            shell_pid=value(shell,'pane_pid');keyboard_pid=value(keyboard,'pane_pid')
            with patch('launch.tmux',side_effect=tmux),patch('launch.sync_server_env'):
                for _ in range(2):
                    launch.toggle_keyboard()
                    self.assertEqual(value(tabs,'pane_height'),'3')
                    self.assertEqual(value(keyboard,'pane_height'),'17')
                    self.assertGreater(int(value(keyboard,'pane_width')),120)
                    launch.toggle_keyboard()
                    self.assertEqual(value(files,'pane_height'),'14')
                    self.assertEqual(value(tabs,'pane_height'),'3')
            self.assertEqual(value(shell,'pane_pid'),shell_pid)
            self.assertEqual(value(keyboard,'pane_pid'),keyboard_pid)
        finally:
            subprocess.run(['tmux','-L',label,'kill-server'],capture_output=True)

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
                from launch import configure_grid_surface
                with patch.dict(os.environ, EDEX_GRID_BACKGROUND='1'):
                    configure_grid_surface(shell, run=tmux)
                files=tmux('split-window','-d','-t',shell,'-v','-P','-F','#{pane_id}','sleep','30')
                pid=tmux('display-message','-p','-t',shell,'#{pane_pid}')
                workspaces.install()
                header=workspaces.option('@edex-tabs')
                workspaces.switch(2)
                second=workspaces.option('@edex-shell')
                self.assertIn('bg=#05080d', tmux('show-options','-p','-v','-t',second,'window-style'))
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


def outside_env(**overrides):
    env={key:value for key,value in os.environ.items()
         if key not in ('TMUX','TMUX_PANE','EDEX_TMUX_SOCKET','EDEX_GRAPHICS_TRANSPORT')}
    env['KITTY_WINDOW_ID']='1'
    env['COLUMNS']='180'
    env['LINES']='55'
    env['TERM']='xterm-kitty'
    env.update(overrides)
    return env


def tmux_client(binary,socket,*args,check=True):
    return subprocess.run([binary,'-L',socket,*args],capture_output=True,text=True,
                          timeout=10,check=check)


def session_option(binary,socket,name):
    return tmux_client(binary,socket,'show-options','-qv','-t','edex',name).stdout.strip()


def pane_value(binary,socket,pane,format_):
    return tmux_client(binary,socket,'display-message','-p','-t',pane,format_).stdout.strip()


def alive_panes(binary,socket):
    return tmux_client(binary,socket,'list-panes','-a','-F','#{pane_id}').stdout.splitlines()


def dead_panes(binary,socket):
    return [pane for pane in alive_panes(binary,socket)
            if pane_value(binary,socket,pane,'#{pane_dead}')!='0']


def child_env(pid):
    try:
        return Path('/proc',str(pid),'environ').read_bytes()
    except OSError:
        return b''


def full_launch(binary,socket,cwd,lock_dir,fps=24):
    result=subprocess.run(
        [sys.executable,str(ROOT/'launch.py'),'--detach','--skip-intro','--files','preview',
         '--cwd',str(cwd),'--fps',str(fps)],
        env=outside_env(EDEX_TMUX_SOCKET=socket,XDG_RUNTIME_DIR=str(lock_dir)),
        capture_output=True,text=True,timeout=180)
    if result.returncode!=0:
        raise AssertionError('launcher failed on '+socket+': '+(result.stderr or result.stdout))
    return result.stdout


def run_cli(binary,script,*args,socket=None,lock_dir=None):
    env=outside_env()
    if socket is not None:env['EDEX_TMUX_SOCKET']=socket
    if lock_dir is not None:env['XDG_RUNTIME_DIR']=str(lock_dir)
    return subprocess.run([sys.executable,str(ROOT/script),*args],env=env,capture_output=True,
                          text=True,timeout=60)


def wait_for(predicate,timeout=20):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if predicate():return True
        time.sleep(.2)
    return bool(predicate())


@contextlib.contextmanager
def attached_client(binary,socket):
    """A real tmux client attached to edex on the socket, fed by a fake 180x55
    terminal; bytes written to the yielded master fd reach the session as keys
    (prefix bindings need b'\\x02' first). A drainer thread keeps the pty from
    filling up on renderer repaints."""
    master,slave=pty.openpty()
    fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',55,180,1440,1080))
    stop=threading.Event();client=None;drainer=None
    try:
        client=subprocess.Popen([binary,'-L',socket,'attach','-t','edex'],stdin=slave,
                                stdout=slave,stderr=slave,env=outside_env())
        def drain():
            while not stop.is_set():
                if select.select([master],[],[],.05)[0]:
                    try:os.read(master,65536)
                    except OSError:return
        drainer=threading.Thread(target=drain,daemon=True);drainer.start()
        if not wait_for(lambda: bool(tmux_client(binary,socket,'list-clients',
                                                 '-F','#{client_pid}',check=False).stdout.strip())):
            raise AssertionError('private tmux client did not attach')
        yield master
    finally:
        stop.set()
        if client is not None:
            client.terminate()
            try:client.wait(timeout=3)
            except subprocess.TimeoutExpired:client.kill();client.wait()
        if drainer is not None:drainer.join(timeout=1)
        os.close(master);os.close(slave)


class TwoServerFixture:
    """Builds two concurrently running private servers, a and b, via real
    launcher subprocesses; every test class owning the fixture gets its own
    pair, named with a class-specific prefix plus the test pid. Servers that
    were started before a setup failure are killed inside setUpClass itself,
    so a broken setup cannot leak a server; tearDownClass repeats the kill
    defensively because it is not guaranteed to run after a setUpClass error."""

    socket_prefix='edex-two-'

    @classmethod
    def setUpClass(cls):
        binary=shutil.which('tmux')
        if binary is None:
            raise AssertionError('tmux is required')
        cls.binary=binary
        cls._dirs=tempfile.TemporaryDirectory(prefix=cls.socket_prefix)
        base=Path(cls._dirs.name);pid=str(os.getpid())
        cls.sockets=[cls.socket_prefix+letter+'-'+pid for letter in 'ab']
        for letter in 'ab':(base/letter).mkdir()
        cls.lock_dir=base/'xdg';cls.lock_dir.mkdir()
        cls.sshells=[]
        started=[]
        try:
            for socket,cwd in zip(cls.sockets,[base/letter for letter in 'ab']):
                stdout=full_launch(binary,socket,cwd,cls.lock_dir)
                started.append(socket)
                if 'tmux -L '+socket+' attach' not in stdout:
                    raise AssertionError('launcher on '+socket+' did not print the attach command')
                shell=session_option(binary,socket,'@edex-shell')
                if not shell:
                    raise AssertionError('@edex-shell missing after launch on '+socket)
                dead=dead_panes(binary,socket)
                if dead:
                    raise AssertionError('dead panes after launch on '+socket+': '+repr(dead))
                cls.sshells.append(shell)
        except BaseException:
            for socket in started:
                subprocess.run([binary,'-L',socket,'kill-server'],capture_output=True,check=False)
            raise

    @classmethod
    def tearDownClass(cls):
        # kill-server on an already-gone server is a no-op.
        for socket in getattr(cls,'sockets',[]):
            subprocess.run([cls.binary,'-L',socket,'kill-server'],capture_output=True,check=False)
        dirs=getattr(cls,'_dirs',None)
        if dirs is not None:dirs.cleanup()


class LauncherSocketIsolationTest(TwoServerFixture,unittest.TestCase):
    """Two private servers built by real launcher subprocesses share the session name
    'edex' and pane IDs. Outside-tmux controls, tmux-spawned keybinding subprocesses,
    and renderer-initiated tab clicks must each reach only their own socket."""

    socket_prefix='edex-iso-'

    def test_keybinding_and_tab_click_select_own_server(self):
        binary,s1,s2=self.binary,self.sockets[0],self.sockets[1]
        shell1,shell2=self.sshells
        with attached_client(binary,s1) as master:
            result=run_cli(binary,'workspaces.py','1',socket=s1,lock_dir=self.lock_dir)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(wait_for(lambda:session_option(binary,s1,'@edex-active-slot')=='1'))
            pid1=pane_value(binary,s1,shell1,'#{pane_pid}')
            path1=pane_value(binary,s1,shell1,'#{pane_current_path}')
            tmux_client(binary,s1,'select-pane','-t',shell1)
            # Digit bindings sit in the prefix table: send Ctrl-b first.
            os.write(master,b'\x022')
            # The digit binding runs workspaces.py in a tmux-spawned subprocess; it must
            # switch this server, not the overlapping one.
            self.assertTrue(wait_for(lambda:session_option(binary,s1,'@edex-active-slot')=='2'))
            self.assertEqual(session_option(binary,s1,'@edex-shell'),session_option(binary,s1,'@edex-slot-2'))
            self.assertEqual(session_option(binary,s2,'@edex-active-slot'),'1')
            self.assertEqual(session_option(binary,s2,'@edex-shell'),shell2)
            tabs=session_option(binary,s1,'@edex-tabs')
            cols,left,top=(int(part) for part in tmux_client(
                binary,s1,'display-message','-p','-t',tabs,
                '#{pane_width},#{pane_left},#{pane_top}').stdout.split(','))
            # Cell x sits in the leftmost fifth of the strip: the 'MAIN SHELL' tab.
            x=left+int((cols-1)/10)+1
            y=top+1
            # The tab strip is a renderer tmux spawned; its click handler switches through
            # the socket the renderer received, so only this server may move.
            os.write(master,f'\x1b[<0;{x};{y}M\x1b[<0;{x};{y}m'.encode())
            self.assertTrue(wait_for(lambda:session_option(binary,s1,'@edex-active-slot')=='1'))
            self.assertEqual(session_option(binary,s1,'@edex-shell'),shell1)
            self.assertEqual(pane_value(binary,s1,shell1,'#{pane_pid}'),pid1)
            self.assertEqual(pane_value(binary,s1,shell1,'#{pane_current_path}'),path1)
            self.assertEqual(pane_value(binary,s1,shell1,'#{pane_dead}'),'0')
            self.assertEqual(session_option(binary,s2,'@edex-shell'),shell2)
            self.assertEqual(session_option(binary,s2,'@edex-slot-2'),'')
            self.assertEqual(dead_panes(binary,s2),[])

    def test_outside_toggle_keyboard_selects_named_server(self):
        binary,s1,s2=self.binary,self.sockets[0],self.sockets[1]
        panes2_before=alive_panes(binary,s2)
        tmux_client(binary,s1,'set-environment','-t','edex','EDEX_GRAPHICS_TRANSPORT','tempfile')
        def keyboard_windows(socket):
            lines=[line.split() for line in
                   tmux_client(binary,socket,'list-panes','-a','-F','#{pane_id} #{pane_title} #{window_name}').stdout.splitlines()]
            return [line[2] for line in lines if len(line)>=3 and line[1]=='Keyboard']
        # First toggle shows the keyboard next to Files in the main window.
        result=run_cli(binary,'launch.py','--toggle-keyboard',socket=s1,lock_dir=self.lock_dir)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(wait_for(lambda:keyboard_windows(s1) and keyboard_windows(s1)!=['_keyboard']))
        self.assertEqual(tmux_client(binary,s1,'show-environment','-t','edex','EDEX_GRAPHICS_TRANSPORT').stdout.strip(),
                         'EDEX_GRAPHICS_TRANSPORT=tempfile')
        keyboard=next(line.split()[0] for line in tmux_client(binary,s1,'list-panes','-a','-F',
                      '#{pane_id} #{pane_title}').stdout.splitlines() if line.split()[1:]==['Keyboard'])
        self.assertIn(b'EDEX_GRAPHICS_TRANSPORT=tempfile',
                      child_env(int(pane_value(binary,s1,keyboard,'#{pane_pid}'))).split(b'\0'))
        self.assertEqual(keyboard_windows(s2),[])
        self.assertEqual(set(alive_panes(binary,s2)),set(panes2_before))
        panes1=alive_panes(binary,s1)
        # Second toggle hides the keyboard back in the detached _keyboard window.
        result=run_cli(binary,'launch.py','--toggle-keyboard',socket=s1,lock_dir=self.lock_dir)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(wait_for(lambda:keyboard_windows(s1)==['_keyboard']))
        self.assertEqual(keyboard_windows(s2),[])
        # Toggling the keyboard moves windows, re-enumerating s1's panes;
        # identities persist, order does not.
        self.assertEqual(set(alive_panes(binary,s1)),set(panes1))
        self.assertEqual(set(alive_panes(binary,s2)),set(panes2_before))

    def test_outside_tmux_workspace_switch_selects_named_server(self):
        binary,s1,s2=self.binary,self.sockets[0],self.sockets[1]
        shell1,shell2=self.sshells
        for socket in (s1,s2):
            result=run_cli(binary,'workspaces.py','1',socket=socket,lock_dir=self.lock_dir)
            self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(session_option(binary,s1,'@edex-active-slot'),'1')
        self.assertEqual(session_option(binary,s1,'@edex-shell'),shell1)
        pid2=pane_value(binary,s2,shell2,'#{pane_pid}')
        path2=pane_value(binary,s2,shell2,'#{pane_current_path}')
        result=run_cli(binary,'workspaces.py','2',socket=s1,lock_dir=self.lock_dir)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(wait_for(lambda:session_option(binary,s1,'@edex-active-slot')=='2'))
        self.assertNotEqual(session_option(binary,s1,'@edex-shell'),shell1)
        self.assertEqual(session_option(binary,s1,'@edex-shell'),session_option(binary,s1,'@edex-slot-2'))
        # The overlapping server keeps its own shell, slot, and shell process.
        self.assertEqual(session_option(binary,s2,'@edex-active-slot'),'1')
        self.assertEqual(session_option(binary,s2,'@edex-shell'),shell2)
        self.assertEqual(session_option(binary,s2,'@edex-slot-2'),'')
        self.assertEqual(pane_value(binary,s2,shell2,'#{pane_pid}'),pid2)
        self.assertEqual(pane_value(binary,s2,shell2,'#{pane_current_path}'),path2)
        self.assertEqual(dead_panes(binary,s2),[])


class StopIsolationTest(TwoServerFixture,unittest.TestCase):
    """launch.py --stop must kill only the session on the selected socket."""

    socket_prefix='edex-stop-'

    def test_outside_stop_selects_named_server_and_preserves_other(self):
        binary=self.binary;s1,s2=self.sockets
        shell2=self.sshells[1]
        pid2=pane_value(binary,s2,shell2,'#{pane_pid}')
        path2=pane_value(binary,s2,shell2,'#{pane_current_path}')
        result=subprocess.run([sys.executable,str(ROOT/'launch.py'),'--stop'],
                              env=outside_env(EDEX_TMUX_SOCKET=s1,XDG_RUNTIME_DIR=str(self.lock_dir)),
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotEqual(tmux_client(binary,s1,'has-session','-t','edex',check=False).returncode,0)
        # The overlapping server keeps running with its shell process intact.
        self.assertEqual(tmux_client(binary,s2,'has-session','-t','edex',check=False).returncode,0)
        self.assertEqual(session_option(binary,s2,'@edex-shell'),shell2)
        self.assertEqual(pane_value(binary,s2,shell2,'#{pane_pid}'),pid2)
        self.assertEqual(pane_value(binary,s2,shell2,'#{pane_current_path}'),path2)
        self.assertEqual(dead_panes(binary,s2),[])
        result=subprocess.run([sys.executable,str(ROOT/'launch.py'),'--stop'],
                              env=outside_env(EDEX_TMUX_SOCKET=s2,XDG_RUNTIME_DIR=str(self.lock_dir)),
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotEqual(tmux_client(binary,s2,'has-session','-t','edex',check=False).returncode,0)


class PreExistingServerSocketTest(unittest.TestCase):
    """The selected server may already be running with unrelated sessions created
    without the selector and without the project tmux.conf; the launcher and its
    tmux-spawned children must still reach it, and the unrelated sessions must
    stay untouched."""

    def test_launch_on_preexisting_server_isolates_children(self):
        binary=shutil.which('tmux')
        self.assertIsNotNone(binary)
        with tempfile.TemporaryDirectory(prefix='edex-socket-pre-') as folder:
            base=Path(folder);lock=base/'xdg';lock.mkdir()
            cwd=base/'cwd';cwd.mkdir()
            cwd2=base/'cwd2';cwd2.mkdir()
            pid=str(os.getpid())
            pre='edex-pre-'+pid
            second='edex-second-'+pid
            try:
                # Unrelated session on the selected socket, created without the
                # selector; an empty config file pins the server so a host
                # ~/.tmux.conf cannot alter key bindings or options.
                result=subprocess.run([binary,'-L',pre,'-f','/dev/null','new-session','-d','-s','other',
                                       '-x','100','-y','30','sleep','300'],
                                      env=outside_env(),capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr)
                other_pane=tmux_client(binary,pre,'list-panes','-t','other','-F','#{pane_id}').stdout.splitlines()[0]
                other_pid=pane_value(binary,pre,other_pane,'#{pane_pid}')
                # An overlapping second server, built by a real launcher subprocess.
                full_launch(binary,second,cwd2,lock)
                second_shell=session_option(binary,second,'@edex-shell')
                self.assertTrue(second_shell)
                # Launch onto the pre-existing server as a real launcher subprocess.
                full_launch(binary,pre,cwd,lock)
                shell=session_option(binary,pre,'@edex-shell')
                self.assertTrue(shell,'@edex-shell missing on pre-existing server')
                # The initial shell is server-spawned; it carries the selector even
                # though the server existed before the launcher.
                environ=child_env(int(pane_value(binary,pre,shell,'#{pane_pid}')))
                self.assertIn(b'EDEX_TMUX_SOCKET='+pre.encode(),environ.split(b'\0'))
                with attached_client(binary,pre) as master:
                    tmux_client(binary,pre,'select-pane','-t',shell)
                    # Digit bindings sit in the prefix table: send Ctrl-b first.
                    os.write(master,b'\x022')
                    # The keybinding subprocess must switch the pre-existing server, not
                    # the second server or the unrelated session.
                    self.assertTrue(wait_for(lambda:session_option(binary,pre,'@edex-active-slot')=='2'))
                    self.assertNotEqual(session_option(binary,pre,'@edex-shell'),shell)
                    self.assertEqual(session_option(binary,pre,'@edex-shell'),session_option(binary,pre,'@edex-slot-2'))
                    self.assertEqual(pane_value(binary,pre,other_pane,'#{pane_pid}'),other_pid)
                    self.assertEqual(pane_value(binary,pre,other_pane,'#{pane_dead}'),'0')
                    self.assertEqual(session_option(binary,second,'@edex-active-slot'),'1')
                    self.assertEqual(session_option(binary,second,'@edex-shell'),second_shell)
                    self.assertEqual(session_option(binary,second,'@edex-slot-2'),'')
                    self.assertEqual(dead_panes(binary,second),[])
            finally:
                for socket in (pre,second):
                    subprocess.run([binary,'-L',socket,'kill-server'],capture_output=True,check=False)


class FullLaunchRejectionTest(unittest.TestCase):
    """A full launch is rejected while TMUX is inherited, before any server is touched."""

    def test_reject_under_inherited_tmux_without_mutating_servers(self):
        binary=shutil.which('tmux')
        self.assertIsNotNone(binary)
        with tempfile.TemporaryDirectory(prefix='edex-socket-reject-') as folder:
            base=Path(folder);lock=base/'xdg';lock.mkdir()
            cwd=base/'cwd';cwd.mkdir()
            socket='edex-reject-'+str(os.getpid())
            try:
                full_launch(binary,socket,cwd,lock)
                shell=session_option(binary,socket,'@edex-shell')
                panes_before=alive_panes(binary,socket)
                socket_path=tmux_client(binary,socket,'display-message','-p','#{socket_path}').stdout.strip()
                for explicit in (True,False):
                    env=outside_env(TMUX=socket_path,XDG_RUNTIME_DIR=str(lock))
                    if explicit:env['EDEX_TMUX_SOCKET']=socket
                    result=subprocess.run([sys.executable,str(ROOT/'launch.py')],env=env,
                                          capture_output=True,text=True,timeout=30)
                    self.assertEqual(result.returncode,2,result.stderr)
                self.assertEqual(session_option(binary,socket,'@edex-shell'),shell)
                self.assertEqual(session_option(binary,socket,'@edex-active-slot'),'1')
                self.assertEqual(alive_panes(binary,socket),panes_before)
                self.assertEqual(dead_panes(binary,socket),[])
            finally:
                subprocess.run([binary,'-L',socket,'kill-server'],capture_output=True,check=False)


class ProfilerSocketTest(unittest.TestCase):
    """Out-of-tmux profiling must profile the socket named by the environment,
    and must not fall back to any other server when that name is unused."""

    def test_profiler_selects_named_socket(self):
        binary=shutil.which('tmux')
        self.assertIsNotNone(binary)
        with tempfile.TemporaryDirectory(prefix='edex-socket-profile-') as folder:
            base=Path(folder);lock=base/'xdg';lock.mkdir()
            cwd=base/'cwd';cwd.mkdir()
            socket='edex-profile-'+str(os.getpid())
            unused=socket+'-unused'
            try:
                full_launch(binary,socket,cwd,lock)
                def profile(sock):
                    return subprocess.run([sys.executable,str(ROOT/'profile_panes.py'),
                                           '--seconds','1','--frames','5'],
                                          env=outside_env(EDEX_TMUX_SOCKET=sock,XDG_RUNTIME_DIR=str(lock)),
                                          cwd=str(ROOT),capture_output=True,text=True,timeout=180)
                result=profile(socket)
                self.assertEqual(result.returncode,0,result.stderr)
                unused_result=profile(unused)
                self.assertNotEqual(unused_result.returncode,0,
                                    'profiler fell back to another server for an unused socket name')
            finally:
                for sock in (socket,unused):
                    subprocess.run([binary,'-L',sock,'kill-server'],capture_output=True,check=False)


if __name__=='__main__':unittest.main()
