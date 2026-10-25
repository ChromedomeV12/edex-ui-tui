"""Border state batching, visibility, and resize-only mutations."""
import os
import shutil
import subprocess
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import border_frame

STATE = ('1,1,0,9,20,123,456;209,49,3,3,203,43;'
         '%0||203|43|1~%1|top|209|2|0~%2|bottom|209|2|0~'
         '%3|left|2|43|0~%4|right|2|43|0~')


class BorderStateTest(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'linux', 'private tmux server')
    def test_normal_stop_does_not_prefix_match_probe_session(self):
        socket = 'edex-exact-stop-' + str(os.getpid())
        binary = shutil.which('tmux')
        self.assertIsNotNone(binary)
        command = [binary, '-L', socket]
        try:
            subprocess.run(command + ['-f', '/dev/null', 'new-session', '-d', '-s',
                                      'edex-border-probe', 'sleep', '30'], check=True)
            env = dict(os.environ, EDEX_TMUX_SOCKET=socket)
            result = subprocess.run([sys.executable, str(Path(border_frame.__file__).parent/'launch.py'),
                                     '--stop'], env=env, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(subprocess.run(command + ['has-session', '-t', '=edex-border-probe']).returncode, 0)
            subprocess.run(command + ['new-session', '-d', '-s', 'edex', 'sleep', '30'], check=True)
            result = subprocess.run([sys.executable, str(Path(border_frame.__file__).parent/'launch.py'),
                                     '--stop'], env=env, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(subprocess.run(command + ['has-session', '-t', '=edex-border-probe']).returncode, 0)
        finally:
            subprocess.run(command + ['kill-server'], capture_output=True)

    def test_idle_snapshot_uses_one_process_and_no_resize(self):
        with patch('border_frame.query', return_value=STATE) as query:
            visible, geometry, client, panes = border_frame._poll('%0')
            self.assertTrue(visible)
            self.assertEqual(geometry, (209, 49, (9, 20), 3, 3, 203, 43))
            self.assertEqual(client, ('123', '456'))
            self.assertFalse(border_frame._fit_gutters(panes))
            query.assert_called_once_with('display-message', '-p', '-t', '%0', border_frame.SNAPSHOT_FORMAT)

    def test_zoom_visibility_and_missing_state(self):
        with patch.dict(os.environ, TMUX_PANE='%1'):
            for state, expected in [(STATE, True), (STATE.replace('1,1,0,', '1,1,1,'), False),
                                    (STATE.replace('1,1,0,', '0,1,0,'), False)]:
                with patch('border_frame.query', return_value=state):
                    self.assertEqual(bool(border_frame._poll('%0')[0]), expected)
        for state in (None, '', '1,1,0;;;', STATE.replace('203|43|1', 'bad|43|1')):
            with patch('border_frame.query', return_value=state):
                self.assertIsNone(border_frame._poll('%0'))

    def test_resize_only_mutates_bands_that_changed(self):
        panes = [('%1', 'top', 209, 2), ('%4', 'right', 4, 43)]
        with patch('border_frame.query', return_value='') as query:
            self.assertTrue(border_frame._fit_gutters(panes))
            query.assert_called_once_with('resize-pane', '-t', '%4', '-x', '2')


if __name__ == '__main__':
    unittest.main()
