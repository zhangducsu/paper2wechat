import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from validate_run import validate_run  # noqa: E402


def write_content(base_dir, file_path="figures/fig1.png"):
    content = {
        "schema_version": 1,
        "metadata": {"title": "Test paper"},
        "sections": {"abstract": "hello"},
        "figures": [
            {
                "id": "fig1",
                "number": 1,
                "caption": "Fig. 1. Test",
                "file_path": file_path,
                "page": 1,
            }
        ],
        "key_data": {},
    }
    path = base_dir / "content.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    return path


class ValidateRunTest(unittest.TestCase):
    def test_passes_when_content_and_markdown_images_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            figures = base / "figures"
            figures.mkdir()
            (figures / "fig1.png").write_bytes(b"fake")
            content_path = write_content(base)
            article_path = base / "article.md"
            article_path.write_text("![figure](figures/fig1.png)\n", encoding="utf-8")

            result = validate_run(content_path=content_path, base_dir=base, article_path=article_path)

            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["error_count"], 0)

    def test_fails_when_content_image_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            content_path = write_content(base)

            result = validate_run(content_path=content_path, base_dir=base)

            self.assertEqual(result["status"], "fail")
            self.assertTrue(any(issue["code"] == "figure_file_missing" for issue in result["issues"]))


if __name__ == "__main__":
    unittest.main()
