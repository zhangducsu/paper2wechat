#!/usr/bin/env python3
"""
微信公众号封面图生成器。

封面背景可以来自 AI 生图结果；脚本只负责本地裁切、标题排版和公司 Logo
水印叠加，避免让 AI 直接生成不可控的文字或 Logo。
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from theme_palette import derive_theme_palette


DEFAULT_WIDTH = 900
DEFAULT_HEIGHT = 383
DEFAULT_SAFE_SIZE = 383
DEFAULT_PRIMARY_COLOR = "#20B2AA"
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#\s+(.+)$", re.M)


def strip_markdown_inline(text: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`~]+", "", text)
    text = re.sub(r"==(.+?)==", r"\1", text)
    return " ".join(text.split())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_hex_color(color: str) -> Tuple[int, int, int]:
    color = color.strip().lstrip("#")
    if len(color) != 6:
        return (32, 178, 170)
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def find_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def read_article_title(article_path: Optional[Path]) -> str:
    if not article_path or not article_path.exists():
        return "微信公众号文章"
    text = article_path.read_text(encoding="utf-8")
    match = HEADING_RE.search(text)
    if match:
        return strip_markdown_inline(match.group(1).strip())
    for line in text.splitlines():
        line = line.strip()
        if line:
            return strip_markdown_inline(re.sub(r"^[#>*\-\s]+", "", line).strip())
    return "微信公众号文章"


def first_article_image(article_path: Optional[Path], figures_dir: Path) -> Optional[Path]:
    if not article_path or not article_path.exists():
        return None
    text = article_path.read_text(encoding="utf-8")
    for ref in IMAGE_RE.findall(text):
        if ref.startswith(("http://", "https://", "data:")):
            continue
        candidate = (article_path.parent / ref).resolve()
        if candidate.exists():
            return candidate
        candidate = (figures_dir / Path(ref).name).resolve()
        if candidate.exists():
            return candidate
    return None


def make_gradient_background(width: int, height: int, primary_color: str) -> Image.Image:
    primary = parse_hex_color(primary_color)
    base = Image.new("RGB", (width, height), "#102027")
    draw = ImageDraw.Draw(base)
    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = tuple(int((1 - ratio) * primary[i] + ratio * 20) for i in range(3))
        draw.line((0, y, width, y), fill=color)
    draw.rectangle((0, int(height * 0.58), width, height), fill=(8, 22, 28))
    draw.rectangle((int(width * 0.05), int(height * 0.12), int(width * 0.95), int(height * 0.88)), outline=(255, 255, 255), width=2)
    return base


def cover_background(background_path: Optional[Path], width: int, height: int, primary_color: str) -> Image.Image:
    if background_path and background_path.exists():
        image = Image.open(background_path).convert("RGB")
        image = ImageOps.fit(image, (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        image = image.filter(ImageFilter.GaussianBlur(radius=1.4))
    else:
        image = make_gradient_background(width, height, primary_color)

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 105))
    return Image.alpha_composite(image.convert("RGBA"), overlay)


def resolve_background(
    article_path: Optional[Path],
    figures_dir: Path,
    background_path: Optional[Path],
    background_source: str,
    require_ai_background: bool,
) -> Tuple[Optional[Path], str]:
    if require_ai_background and background_source != "ai_generated":
        raise ValueError("--require-ai-background 需要同时设置 --background-source ai_generated")

    if background_source == "ai_generated":
        if not background_path or not background_path.exists():
            raise ValueError("AI 封面背景不存在，请先提供有效的 --background")
        return background_path, "ai_generated"

    if background_source == "local_gradient":
        return None, "local_gradient"

    if background_source == "manual_image" and not background_path:
        raise ValueError("--background-source manual_image 需要同时提供 --background")

    if background_path:
        if not background_path.exists():
            raise ValueError(f"背景图片不存在: {background_path}")
        return background_path, "manual_image"

    article_background = first_article_image(article_path, figures_dir)
    if article_background:
        return article_background, "article_image"
    if background_source == "article_image":
        raise ValueError("未在文章中找到可用的封面背景图片")

    return None, "local_gradient"


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    lines: List[str] = []
    current = ""
    for char in text:
        trial = current + char
        if text_size(draw, trial, font)[0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines


def fit_title_lines(draw: ImageDraw.ImageDraw, title: str, max_width: int, max_lines: int = 3) -> Tuple[ImageFont.ImageFont, List[str]]:
    for size in range(42, 23, -2):
        font = find_font(size, bold=True)
        lines = wrap_text(draw, title, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
    font = find_font(24, bold=True)
    lines = wrap_text(draw, title, font, max_width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip("，。；：、") + "..."
    return font, lines


def apply_logo_watermark(canvas: Image.Image, logo_path: Path, safe_box: Tuple[int, int, int, int]) -> bool:
    if not logo_path.exists():
        return False
    logo = Image.open(logo_path).convert("RGBA")
    max_side = 72
    logo.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

    alpha = logo.getchannel("A").point(lambda value: int(value * 0.62))
    logo.putalpha(alpha)

    x0, y0, x1, y1 = safe_box
    x = x1 - logo.width - 18
    y = y1 - logo.height - 18
    canvas.alpha_composite(logo, (x, y))
    return True


def draw_cover_text(
    canvas: Image.Image,
    title: str,
    subtitle: str,
    primary_color: str,
    safe_box: Tuple[int, int, int, int],
) -> None:
    draw = ImageDraw.Draw(canvas)
    x0, y0, x1, y1 = safe_box
    max_width = x1 - x0 - 56
    title_font, title_lines = fit_title_lines(draw, title, max_width=max_width)
    subtitle_font = find_font(17)
    label_font = find_font(15, bold=True)

    primary = parse_hex_color(primary_color)
    label = "文献解读"
    label_w, label_h = text_size(draw, label, label_font)
    label_x = x0 + 28
    label_y = y0 + 40
    draw.rounded_rectangle(
        (label_x - 12, label_y - 8, label_x + label_w + 12, label_y + label_h + 10),
        radius=10,
        fill=(*primary, 220),
    )
    draw.text((label_x, label_y), label, font=label_font, fill=(255, 255, 255, 255))

    line_heights = [text_size(draw, line, title_font)[1] + 12 for line in title_lines]
    total_title_height = sum(line_heights)
    start_y = y0 + 110
    for line, line_height in zip(title_lines, line_heights):
        line_w, line_h = text_size(draw, line, title_font)
        draw.text((x0 + (x1 - x0 - line_w) / 2, start_y), line, font=title_font, fill=(255, 255, 255, 255))
        start_y += line_height

    if subtitle:
        subtitle_lines = wrap_text(draw, subtitle, subtitle_font, max_width)
        subtitle_lines = subtitle_lines[:2]
        y = start_y + 8
        for line in subtitle_lines:
            line_w, _ = text_size(draw, line, subtitle_font)
            draw.text((x0 + (x1 - x0 - line_w) / 2, y), line, font=subtitle_font, fill=(235, 245, 245, 235))
            y += 24


def create_cover(
    article_path: Optional[Path],
    output_path: Path,
    square_output_path: Optional[Path],
    figures_dir: Path,
    logo_path: Path,
    title: Optional[str],
    subtitle: str,
    background_path: Optional[Path],
    width: int,
    height: int,
    safe_size: int,
    primary_color: str,
    background_source: str = "auto",
    require_ai_background: bool = False,
) -> Dict[str, Any]:
    resolved_title = title or read_article_title(article_path)
    resolved_background, resolved_background_source = resolve_background(
        article_path=article_path,
        figures_dir=figures_dir,
        background_path=background_path,
        background_source=background_source,
        require_ai_background=require_ai_background,
    )
    canvas = cover_background(resolved_background, width, height, primary_color)

    safe_x0 = int((width - safe_size) / 2)
    safe_box = (safe_x0, 0, safe_x0 + safe_size, height)

    vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(vignette)
    draw.rectangle((safe_box[0], safe_box[1], safe_box[2], safe_box[3]), fill=(0, 0, 0, 40))
    canvas = Image.alpha_composite(canvas, vignette)

    draw_cover_text(canvas, resolved_title, subtitle, primary_color, safe_box)
    logo_applied = apply_logo_watermark(canvas, logo_path, safe_box)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, format="PNG")

    square_path = None
    if square_output_path:
        square_output_path.parent.mkdir(parents=True, exist_ok=True)
        square = canvas.crop((safe_box[0], safe_box[1], safe_box[2], safe_box[3]))
        square.convert("RGB").save(square_output_path, format="PNG")
        square_path = square_output_path

    ai_generated_background = resolved_background_source == "ai_generated"

    return {
        "schema_version": 1,
        "created_at": utc_now(),
        "status": "pass",
        "mode": "ai_background_logo_composite" if ai_generated_background else "local_pillow_logo_composite",
        "title": resolved_title,
        "subtitle": subtitle,
        "output": str(output_path),
        "square_output": str(square_path) if square_path else None,
        "size": f"{width}x{height}",
        "safe_square": f"{safe_size}x{safe_size}",
        "background": str(resolved_background) if resolved_background else None,
        "background_source": resolved_background_source,
        "ai_generated_background": ai_generated_background,
        "logo": str(logo_path),
        "logo_watermark_applied": logo_applied,
        "ai_watermark": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="生成微信公众号封面图")
    parser.add_argument("--article", help="文章 Markdown 路径，用于读取标题和首图")
    parser.add_argument("--title", help="封面标题；默认读取文章一级标题")
    parser.add_argument("--subtitle", default="学术论文 · 微信公众号解读", help="封面副标题")
    parser.add_argument("--output", required=True, help="封面输出路径，默认建议 900x383 PNG")
    parser.add_argument("--square-output", help="可选：中心安全区 383x383 方图输出路径")
    parser.add_argument("--figures-dir", default="output/figures", help="文章图片目录")
    parser.add_argument("--background", help="可选：指定背景图片；默认使用文章首图")
    parser.add_argument(
        "--background-source",
        choices=["auto", "ai_generated", "manual_image", "article_image", "local_gradient"],
        default="auto",
        help="背景来源标记；AI 生图背景必须设置为 ai_generated",
    )
    parser.add_argument(
        "--require-ai-background",
        action="store_true",
        help="强制要求 --background 指向 AI 生图背景",
    )
    parser.add_argument("--logo", default=".claude/templates/references/global_assets/logo.jpg", help="公司 Logo 路径")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--safe-size", type=int, default=DEFAULT_SAFE_SIZE)
    parser.add_argument("--primary-color", default=DEFAULT_PRIMARY_COLOR)
    parser.add_argument("--theme-logo", help="从公司 Logo 自动提取主题色；默认可与 --logo 相同")
    parser.add_argument("--palette-output", help="可选：输出 Logo 调色板 JSON")
    parser.add_argument("--json-output", help="可选：生成报告 JSON")
    args = parser.parse_args()

    logo_path = Path(args.logo)
    palette = derive_theme_palette(Path(args.theme_logo)) if args.theme_logo else None
    primary_color = palette["primary"] if palette else args.primary_color

    try:
        report = create_cover(
            article_path=Path(args.article) if args.article else None,
            output_path=Path(args.output),
            square_output_path=Path(args.square_output) if args.square_output else None,
            figures_dir=Path(args.figures_dir),
            logo_path=logo_path,
            title=args.title,
            subtitle=args.subtitle,
            background_path=Path(args.background) if args.background else None,
            width=args.width,
            height=args.height,
            safe_size=args.safe_size,
            primary_color=primary_color,
            background_source=args.background_source,
            require_ai_background=args.require_ai_background,
        )
        if palette:
            report["theme_palette"] = palette
    except ValueError as exc:
        report = {
            "schema_version": 1,
            "created_at": utc_now(),
            "status": "fail",
            "error": str(exc),
        }
        text = json.dumps(report, ensure_ascii=False, indent=2)
        print(text)
        if args.json_output:
            output = Path(args.json_output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text + "\n", encoding="utf-8")
        return 2

    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if palette and args.palette_output:
        output = Path(args.palette_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(palette, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json_output:
        output = Path(args.json_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
