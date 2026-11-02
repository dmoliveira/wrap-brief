"""Initial fixture payload budget, without browser/developer dependencies."""

import gzip
import unittest
from pathlib import Path

from fixtures.support import read_json

from wrap_brief.render.digest import render_digest
from wrap_brief.state.snapshot import Snapshot


class ReaderBudgetTests(unittest.TestCase):
    def test_all_fixture_initial_assets_fit_compressed_budget(self):
        css = (Path(__file__).resolve().parents[2] / "web" / "styles.css").read_bytes()
        for case in ("digest", "corrected", "empty"):
            with self.subTest(case=case):
                html = render_digest(Snapshot.from_dict(read_json(f"views/{case}.json")))
                self.assertEqual(html.count('rel="stylesheet"'), 1)
                self.assertNotIn("<script", html)
                self.assertNotIn("<img", html)
                size = sum(len(gzip.compress(asset, mtime=0)) for asset in (html.encode(), css))
                self.assertLessEqual(size, 150_000)
