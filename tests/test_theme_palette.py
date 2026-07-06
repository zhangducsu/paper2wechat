import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from theme_palette import derive_theme_palette  # noqa: E402


class ThemePaletteTest(unittest.TestCase):
    def test_derives_primary_and_harmony_from_multicolor_logo(self):
        with tempfile.TemporaryDirectory() as tmp:
            logo = Path(tmp) / "logo.png"
            image = Image.new("RGB", (120, 60), "#ffffff")
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, 80, 60), fill="#0066CC")
            draw.rectangle((80, 0, 120, 60), fill="#FF9900")
            image.save(logo)

            result = derive_theme_palette(logo)

            self.assertTrue(result["primary"].startswith("#"))
            self.assertIn(result["primary"], result["logo_colors"])
            self.assertIn("secondary", result["palette"])
            self.assertIn("soft_background", result["palette"])


if __name__ == "__main__":
    unittest.main()
