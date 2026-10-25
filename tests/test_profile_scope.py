"""Profiling must not count unrelated sessions or PID reuse as project CPU."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from profile_panes import project_processes,process_usage


class ScopeTest(unittest.TestCase):
    def test_includes_kitty_client_and_descendants_without_unrelated_apps(self):
        parents={1:0,10:1,11:10,20:1,21:20,22:21,30:1}
        rows={pid:dict(parent=parent,name='kitty' if pid==10 else 'process',
              start='1',ticks=10,rss=1024) for pid,parent in parents.items()}
        scope=project_processes(rows,20,[11])
        self.assertEqual(set(scope),{10,11,20,21,22})
        after={pid:dict(row,ticks=30) for pid,row in rows.items()}
        after[22]['start']='reused'
        groups=process_usage(rows,after,scope,scope,1)
        self.assertEqual(groups['session descendants']['processes'],2)
        import os
        self.assertEqual(groups['session descendants']['cpu_percent_one_core'],round(20/os.sysconf('SC_CLK_TCK')*100,2))


if __name__=='__main__':unittest.main()
