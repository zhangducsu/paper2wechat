import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude" / "scripts"

import sys

sys.path.insert(0, str(SCRIPTS))

from md2wechat import render_markdown_file  # noqa: E402
from validate_run import validate_run  # noqa: E402


class QualityFixtureTest(unittest.TestCase):
    def test_sample_article_renders_and_validates(self):
        fixtures = ROOT / "tests" / "fixtures"
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "sample_article.html"

            render_markdown_file(
                input_path=fixtures / "sample_article.md",
                output_path=html_path,
                theme="default",
                template=None,
                inline_template=None,
                primary_color="#20B2AA",
            )
            result = validate_run(
                content_path=fixtures / "content.json",
                base_dir=fixtures,
                article_path=fixtures / "sample_article.md",
                html_path=html_path,
                output_dir=fixtures,
            )

            self.assertEqual(result["status"], "pass")
            html = html_path.read_text(encoding="utf-8")
            self.assertNotIn("<script", html.lower())
            self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
