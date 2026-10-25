"""Run from any directory; each integration test owns its private tmux server."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
env = dict(os.environ, PYTHONPATH=str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', ''))
names = ['test_port.py', 'test_provenance.py', 'test_packaging.py', 'test_local_transport.py', 'test_background.py', 'test_palette.py', 'test_border_state.py', 'test_tmux_recovery.py', 'test_layout.py', 'test_render_optimization.py', 'test_workspaces.py', 'test_keyboard_touch.py', 'test_popups.py', 'test_profile_scope.py', 'test_yazi_navigation.py']
failed = []
for name in names:
    result = subprocess.run([sys.executable, str(ROOT/'tests'/name)], cwd=ROOT, env=env)
    if result.returncode:
        failed.append(name)
try:
    result = subprocess.run(['lua', 'tests/test_grid.lua'], cwd=ROOT)
    if result.returncode:
        failed.append('test_grid.lua')
except FileNotFoundError:
    failed.append('test_grid.lua (lua missing)')
if failed:
    print('Failed: ' + ', '.join(failed), file=sys.stderr)
    sys.exit(1)
print('All checks passed.')
