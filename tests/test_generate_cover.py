import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from generate_cover import create_cover, read_article_title  # noqa: E402
from validate_run import validate_cover, validate_cover_report  # noqa: E402


class GenerateCoverTest(unittest.TestCase):
    def test_generates_cover_square_preview_and_logo_watermark(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            figures = base / "figures"
            figures.mkdir()
            background = figures / "fig1.png"
            logo = base / "logo.jpg"
            article = base / "article.md"
            cover = base / "cover.png"
            square = base / "cover_square.png"

            Image.new("RGB", (500, 300), "#336699").save(background)
            Image.new("RGB", (120, 80), "#ffffff").save(logo)
            article.write_text("# 测试封面标题\n\n![图](figures/fig1.png)\n", encoding="utf-8")

            report = create_cover(
                article_path=article,
                output_path=cover,
                square_output_path=square,
                figures_dir=figures,
                logo_path=logo,
                title=None,
                subtitle="测试副标题",
                background_path=background,
                width=900,
                height=383,
                safe_size=383,
                primary_color="#20B2AA",
                background_source="ai_generated",
                require_ai_background=True,
            )

            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["mode"], "ai_background_logo_composite")
            self.assertEqual(report["background_source"], "ai_generated")
            self.assertTrue(report["ai_generated_background"])
            self.assertFalse(report["ai_watermark"])
            self.assertTrue(report["logo_watermark_applied"])
            self.assertEqual(validate_cover(cover), [])

            with Image.open(cover) as image:
                self.assertEqual(image.size, (900, 383))
            with Image.open(square) as image:
                self.assertEqual(image.size, (383, 383))

    def test_cover_report_validation_requires_ai_background(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            background = base / "ai_background.png"
            logo = base / "logo.jpg"
            article = base / "article.md"
            cover = base / "cover.png"
            report_path = base / "cover_report.json"

            Image.new("RGB", (500, 300), "#336699").save(background)
            Image.new("RGB", (120, 80), "#ffffff").save(logo)
            article.write_text("# 测试封面标题\n", encoding="utf-8")

            report = create_cover(
                article_path=article,
                output_path=cover,
                square_output_path=None,
                figures_dir=base,
                logo_path=logo,
                title=None,
                subtitle="测试副标题",
                background_path=background,
                width=900,
                height=383,
                safe_size=383,
                primary_color="#20B2AA",
                background_source="ai_generated",
                require_ai_background=True,
            )
            report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

            self.assertEqual(validate_cover_report(report_path, require_ai_cover=True), [])

    def test_requires_ai_background_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            logo = base / "logo.jpg"
            cover = base / "cover.png"
            Image.new("RGB", (120, 80), "#ffffff").save(logo)

            with self.assertRaises(ValueError):
                create_cover(
                    article_path=None,
                    output_path=cover,
                    square_output_path=None,
                    figures_dir=base,
                    logo_path=logo,
                    title="测试封面标题",
                    subtitle="测试副标题",
                    background_path=None,
                    width=900,
                    height=383,
                    safe_size=383,
                    primary_color="#20B2AA",
                    background_source="auto",
                    require_ai_background=True,
                )

    def test_article_title_is_plain_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            article = Path(tmp) / "article.md"
            article.write_text("# *Research* | ==重点== `GENE1`\n", encoding="utf-8")

            self.assertEqual(read_article_title(article), "Research | 重点 GENE1")


if __name__ == "__main__":
    unittest.main()
