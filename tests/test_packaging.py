"""Check staged assets and launcher routing without installing or opening a window."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app

spec = importlib.util.spec_from_file_location('edex_package_install', ROOT / 'packaging/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class PackagingTest(unittest.TestCase):
    def test_ssh_without_display_uses_current_terminal_and_separate_session(self):
        with patch.dict(os.environ, {'SSH_CONNECTION': 'fixture', 'TERM': 'xterm-kitty',
                                     'EDEX_GRAPHICS_TRANSPORT': 'tempfile', 'EDEX_GRID_BACKGROUND': '1'}, clear=True):
            args, env = app.command(['--cwd', '/tmp/a b;$x'])
            self.assertEqual(args[0], sys.executable)
            self.assertNotIn('kitty', args)
            self.assertEqual(args[-2:], ['--cwd', '/tmp/a b;$x'])
            self.assertEqual(env['EDEX_GRAPHICS_TRANSPORT'], 'direct')
            self.assertTrue(env['EDEX_TMUX_SOCKET'].endswith('-direct'))
            self.assertNotIn('EDEX_GRID_BACKGROUND', env)
            self.assertEqual(os.environ['EDEX_GRAPHICS_TRANSPORT'], 'tempfile')
            controls, control_env = app.command(['--toggle-keyboard'])
            self.assertEqual(controls[-1], '--toggle-keyboard')
            self.assertEqual(control_env['EDEX_TMUX_SOCKET'], env['EDEX_TMUX_SOCKET'])

    def test_inline_rejects_host_file_transfer_and_unrecognized_terminal(self):
        with patch.dict(os.environ, {'TERM': 'xterm-kitty'}, clear=True):
            args, env = app.command(['--in-place'])
            self.assertNotIn('--in-place', args)
            for transport in (['--graphics-transport', 'tempfile'], ['--graphics-transport=tempfile']):
                with self.assertRaisesRegex(ValueError, 'direct transfer'):
                    app.command(['--in-place', *transport])
        with patch.dict(os.environ, {'SSH_TTY': '/dev/pts/fixture', 'TERM': 'xterm-256color'}, clear=True):
            with self.assertRaisesRegex(ValueError, 'Graphics client not recognized'):
                app.command([])
            self.assertEqual(app.command(['--help'])[0][-1], '--help')
            compatible, compatible_env = app.command(['--in-place'])
            self.assertEqual(compatible[0], sys.executable)
            self.assertEqual(compatible_env['TERM'], 'xterm-256color')
            self.assertEqual(compatible_env['EDEX_GRAPHICS_TRANSPORT'], 'direct')

    def test_inline_keeps_nested_tmux_guard_and_requires_a_real_pty(self):
        with patch.dict(os.environ, {'TERM': 'xterm-kitty', 'TMUX': 'existing',
                                     'EDEX_TMUX_SOCKET': 'edex-explicit'}, clear=True):
            _, env = app.command(['--in-place'])
            self.assertEqual(env['TMUX'], 'existing')
            self.assertEqual(env['EDEX_TMUX_SOCKET'], 'edex-explicit')
            with patch.object(sys, 'argv', ['edex-ui-tui', '--in-place']), \
                    patch.object(sys.stdin, 'isatty', return_value=False), \
                    patch('os.execvpe') as execute:
                with self.assertRaises(SystemExit) as exit_status:
                    app.main()
                self.assertEqual(exit_status.exception.code, 2)
                execute.assert_not_called()

    def test_staged_tree_contains_manifest_assets_and_loads_outside_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)
            installer.stage(dest, package_name='edex-ui-tui-git')
            runtime = dest / 'usr/share/edex-ui-tui'
            manifest = json.loads((runtime / 'UPSTREAM.json').read_text())
            for row in manifest['files'] + [r for r in manifest['derived_assets'] if 'sha256' in r]:
                path = row.get('local_path', row.get('path'))
                with self.subTest(path=path):
                    self.assertEqual(hashlib.sha256((runtime / path).read_bytes()).hexdigest(), row['sha256'])
            names = {p.relative_to(runtime).as_posix() for p in runtime.rglob('*') if p.is_file()}
            self.assertNotIn('border_probe.py', names)
            self.assertNotIn('profile_panes.py', names)
            self.assertFalse(any(p.startswith(('tests/', 'docs/', '.git/')) or '__pycache__' in p for p in names))
            self.assertTrue((dest / 'usr/share/licenses/edex-ui-tui-git/OFL.txt').is_file())
            self.assertTrue((dest / 'usr/share/licenses/edex-ui-tui-git/NOTICE.md').is_file())
            self.assertFalse((dest / 'usr/share/licenses/edex-ui-tui').exists())
            self.assertTrue((dest / 'usr/share/applications/edex-ui-tui.desktop').is_file())
            code = ('from pathlib import Path; import app, background, render, palette; '
                    'assert Path(app.__file__).resolve().parent == Path.cwd(); '
                    'assert background.grid_tile().size == (22, 22); '
                    'assert render.font(16).getbbox("eDEX"); '
                    'assert palette.FG == "#aacfd1"; '
                    'assert str(Path.cwd()/"launch.py") in app.command(["--help"])[0]')
            if sys.platform != 'win32':
                code += '; import importlib; [importlib.import_module(name) for name in ' + repr(installer.MODULES) + ']'
            subprocess.run([sys.executable, '-I', '-c', 'import sys;sys.path.insert(0,".");' + code],
                           cwd=runtime, check=True, capture_output=True, text=True)
            with self.assertRaises(ValueError):
                installer.stage(dest / 'rejected', package_name='../outside')

    def test_distribution_interpreter_does_not_change_runtime_files(self):
        with tempfile.TemporaryDirectory() as directory:
            dest=Path(directory)
            installer.stage(dest/'arch')
            installer.stage(dest/'ubuntu', interpreter='/usr/bin/python3')
            first=(dest/'arch/usr/bin/edex-ui-tui').read_text()
            second=(dest/'ubuntu/usr/bin/edex-ui-tui').read_text()
            self.assertIn('exec /usr/bin/python ', first)
            self.assertIn('exec /usr/bin/python3 ', second)
            for relative in [p.relative_to(dest/'arch/usr/share/edex-ui-tui')
                             for p in (dest/'arch/usr/share/edex-ui-tui').rglob('*') if p.is_file()]:
                self.assertEqual((dest/'arch/usr/share/edex-ui-tui'/relative).read_bytes(),
                                 (dest/'ubuntu/usr/share/edex-ui-tui'/relative).read_bytes())

    def test_launcher_keeps_argument_boundaries_and_scopes_environment(self):
        with patch.dict(os.environ, {'TMUX': 'outside', 'TMUX_PANE': '%1',
                                     'EDEX_TMUX_SOCKET': 'edex-example'}, clear=True):
            args, env = app.command(['--cwd', '/tmp/a b;$x'])
            self.assertEqual(args[-2:], ['--cwd', '/tmp/a b;$x'])
            self.assertEqual(args[0], 'kitty')
            self.assertNotIn('TMUX', env)
            self.assertNotIn('TMUX_PANE', env)
            self.assertEqual(env['EDEX_GRID_BACKGROUND'], '1')
            self.assertEqual(env['EDEX_TMUX_SOCKET'], 'edex-example')
            self.assertEqual(os.environ['TMUX'], 'outside')
            for flag in app.CONTROLS:
                argv, control_env = app.command([flag])
                self.assertEqual(argv[0], sys.executable)
                self.assertNotIn('kitty', argv)
                self.assertEqual(control_env['TMUX'], 'outside')


if __name__ == '__main__':
    unittest.main()
