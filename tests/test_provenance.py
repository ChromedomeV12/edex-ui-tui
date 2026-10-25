"""Check bundled artifact digests without fetching upstream or using a lab clone."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ProvenanceTest(unittest.TestCase):
    def test_declared_bundled_artifacts_match_the_manifest(self):
        manifest=json.loads((ROOT/'UPSTREAM.json').read_text())
        rows=manifest['files']+[row for row in manifest['derived_assets'] if 'sha256' in row]
        self.assertTrue(rows)
        for row in rows:
            path=row.get('local_path',row.get('path'))
            with self.subTest(path=path):
                actual=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
                self.assertEqual(actual,row['sha256'])


if __name__=='__main__':unittest.main()
