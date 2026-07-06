import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from sync_assets import copy_assets, normalize_article  # noqa: E402


class SyncAssetsTest(unittest.TestCase):
    def test_copies_assets_and_rewrites_global_asset_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "global_assets"
            figures = base / "figures"
            source.mkdir()
            (source / "logo.jpg").write_bytes(b"fake-logo")
            article = base / "article.md"
            article.write_text("![logo](global_assets/logo.jpg)\n", encoding="utf-8")

            copied = copy_assets(source, figures)
            changed = normalize_article(article)

            self.assertEqual(len(copied), 1)
            self.assertTrue((figures / "logo.jpg").exists())
            self.assertTrue(changed)
            self.assertIn("figures/logo.jpg", article.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
