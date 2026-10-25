"""Keep shared artwork and terminal colors tied to the pinned eDEX theme."""
from pathlib import Path
import re
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from palette import FG,BG,PRIMARY,blend,terminal_colors


class PaletteTest(unittest.TestCase):
    def test_source_colors_and_alpha_states(self):
        self.assertEqual(FG,'#aacfd1');self.assertEqual(BG,'#05080d')
        self.assertEqual(PRIMARY,(170,207,209))
        self.assertEqual(blend(.1),'#161c21')
        self.assertEqual(blend(.3),'#374448')
        self.assertEqual(blend(.5),'#586c6f')

    def test_terminal_config_matches_upstream_derived_ansi_slots(self):
        config=(Path(__file__).resolve().parents[1]/'kitty.conf').read_text()
        slots={int(i):color for i,color in re.findall(r'^color(\d+) (#[0-9a-f]{6})$',config,re.M)}
        self.assertEqual([slots[i] for i in range(16)],terminal_colors())
        self.assertIn('foreground '+FG,config)
        self.assertIn('selection_background '+blend(.3),config)


if __name__=='__main__':unittest.main()
