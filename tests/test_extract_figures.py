import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from extract_figures import extract_figures  # noqa: E402


def png_bytes(color):
    buffer = io.BytesIO()
    Image.new("RGB", (260, 260), color=color).save(buffer, format="PNG")
    return buffer.getvalue()


class ExtractFiguresTest(unittest.TestCase):
    def test_extracts_stable_unique_figure_files_and_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pdf_path = tmp_path / "sample.pdf"
            output_dir = tmp_path / "figures"

            doc = fitz.open()
            page = doc.new_page(width=500, height=700)
            page.insert_text((40, 40), "Fig. 1. First figure")
            page.insert_image(fitz.Rect(40, 70, 300, 330), stream=png_bytes("red"))
            page.insert_text((40, 360), "Fig. 2. Second figure")
            page.insert_image(fitz.Rect(40, 390, 300, 650), stream=png_bytes("blue"))
            doc.save(pdf_path)
            doc.close()

            figures = extract_figures(str(pdf_path), str(output_dir))

            self.assertEqual([figure["file"] for figure in figures], ["fig1.png", "fig2.png"])
            self.assertEqual([figure["number"] for figure in figures], [1, 2])
            self.assertEqual([figure["source_number"] for figure in figures], [1, 2])
            self.assertTrue((output_dir / "fig1.png").exists())
            self.assertTrue((output_dir / "fig2.png").exists())

            figure_map = json.loads((output_dir / "figure_map.json").read_text(encoding="utf-8"))
            self.assertEqual(figure_map["schema_version"], 2)
            self.assertEqual(len(figure_map["figures"]), 2)


if __name__ == "__main__":
    unittest.main()
