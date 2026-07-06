#!/usr/bin/env python3
"""
从公司 Logo 提取推文主题色。
"""

from __future__ import annotations

import argparse
import colorsys
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image


FALLBACK_PRIMARY = "#20B2AA"


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def hex_to_rgb(color: str) -> Tuple[int, int, int]:
    color = color.strip().lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def shift_hue(rgb: Tuple[int, int, int], shift: float, saturation: float | None = None, value: float | None = None) -> str:
    h, s, v = colorsys.rgb_to_hsv(*(channel / 255 for channel in rgb))
    r, g, b = colorsys.hsv_to_rgb((h + shift) % 1.0, saturation if saturation is not None else s, value if value is not None else v)
    return rgb_to_hex((round(r * 255), round(g * 255), round(b * 255)))


def mix_with_white(rgb: Tuple[int, int, int], ratio: float) -> str:
    mixed = tuple(round(channel * (1 - ratio) + 255 * ratio) for channel in rgb)
    return rgb_to_hex(mixed)


def logo_color_candidates(logo_path: Path) -> List[Dict[str, Any]]:
    image = Image.open(logo_path).convert("RGBA")
    image.thumbnail((160, 160), Image.Resampling.LANCZOS)

    pixels: Dict[Tuple[int, int, int], int] = {}
    loaded = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = loaded[x, y]
            if a < 128:
                continue
            if max(r, g, b) > 245 and max(r, g, b) - min(r, g, b) < 16:
                continue
            if max(r, g, b) < 35:
                continue
            key = (round(r / 16) * 16, round(g / 16) * 16, round(b / 16) * 16)
            key = tuple(min(255, value) for value in key)
            pixels[key] = pixels.get(key, 0) + 1

    candidates = []
    total = sum(pixels.values()) or 1
    for rgb, count in pixels.items():
        h, s, v = colorsys.rgb_to_hsv(*(channel / 255 for channel in rgb))
        if s < 0.18 or v < 0.25:
            continue
        candidates.append(
            {
                "hex": rgb_to_hex(rgb),
                "rgb": rgb,
                "weight": count,
                "share": round(count / total, 4),
                "score": count * (0.35 + s) * (0.45 + v),
            }
        )
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates


def derive_theme_palette(logo_path: Path) -> Dict[str, Any]:
    candidates = logo_color_candidates(logo_path)
    primary = candidates[0]["hex"] if candidates else FALLBACK_PRIMARY
    primary_rgb = hex_to_rgb(primary)

    return {
        "schema_version": 1,
        "source": str(logo_path),
        "primary": primary,
        "palette": {
            "primary": primary,
            "secondary": shift_hue(primary_rgb, 1 / 12, saturation=0.62),
            "accent": shift_hue(primary_rgb, -1 / 12, saturation=0.72),
            "complement": shift_hue(primary_rgb, 0.5, saturation=0.55, value=0.86),
            "soft_background": mix_with_white(primary_rgb, 0.88),
            "border": mix_with_white(primary_rgb, 0.68),
        },
        "logo_colors": [item["hex"] for item in candidates[:5]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="从公司 Logo 提取推文主题色")
    parser.add_argument("logo", help="Logo 图片路径")
    parser.add_argument("--json-output", help="可选：写入调色板 JSON")
    args = parser.parse_args()

    palette = derive_theme_palette(Path(args.logo))
    text = json.dumps(palette, ensure_ascii=False, indent=2)
    print(text)
    if args.json_output:
        output = Path(args.json_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
