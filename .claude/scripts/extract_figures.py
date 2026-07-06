#!/usr/bin/env python3
"""
PDF Figure 提取器。

设计目标：
- 文件名按论文中出现顺序稳定生成：fig1.png, fig2.jpeg ...
- 使用图片哈希去重，避免同一张图被重复提取；
- caption 只作为元数据，不再用来直接决定文件名，避免 fig2 缺失/fig3 重复。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF


CAPTION_RE = re.compile(r"\b(?:Fig\.?|Figure)\s*([0-9]+)([A-Za-z]?)\b[.:]?\s*(.*)", re.IGNORECASE)


def normalize_caption(text: str) -> str:
    return " ".join(text.split())


def extract_caption_candidates(doc: fitz.Document) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for page_index in range(len(doc)):
        page = doc[page_index]
        for line_index, raw_line in enumerate(page.get_text().splitlines()):
            line = normalize_caption(raw_line)
            if not line:
                continue
            match = CAPTION_RE.search(line)
            if not match:
                continue
            candidates.append(
                {
                    "page": page_index + 1,
                    "line_index": line_index,
                    "source_number": int(match.group(1)),
                    "source_suffix": match.group(2) or "",
                    "caption": line,
                }
            )
    return candidates


def image_sort_key(item: Dict[str, Any]) -> tuple:
    rect = item.get("rect") or {}
    return (item["page"], rect.get("y0", 0), rect.get("x0", 0), item["image_index"])


def collect_images(doc: fitz.Document, min_width: int, min_height: int) -> List[Dict[str, Any]]:
    images: List[Dict[str, Any]] = []
    seen_hashes = set()

    for page_index in range(len(doc)):
        page = doc[page_index]
        for image_index, image in enumerate(page.get_images(full=True)):
            xref = image[0]
            try:
                extracted = doc.extract_image(xref)
            except Exception as exc:  # noqa: BLE001
                print(f"Warning: failed to extract image {image_index} on page {page_index + 1}: {exc}")
                continue

            width = int(extracted.get("width", 0))
            height = int(extracted.get("height", 0))
            if width < min_width or height < min_height:
                continue

            image_bytes = extracted["image"]
            digest = hashlib.sha256(image_bytes).hexdigest()
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)

            rects = page.get_image_rects(xref)
            rect = rects[0] if rects else None
            images.append(
                {
                    "page": page_index + 1,
                    "image_index": image_index,
                    "xref": xref,
                    "width": width,
                    "height": height,
                    "ext": extracted["ext"],
                    "bytes": image_bytes,
                    "sha256": digest,
                    "rect": {
                        "x0": round(rect.x0, 2),
                        "y0": round(rect.y0, 2),
                        "x1": round(rect.x1, 2),
                        "y1": round(rect.y1, 2),
                    }
                    if rect
                    else None,
                }
            )

    return sorted(images, key=image_sort_key)


def pick_caption(
    image: Dict[str, Any],
    captions: List[Dict[str, Any]],
    used_caption_indexes: set,
) -> Optional[Dict[str, Any]]:
    same_page = [
        (idx, caption)
        for idx, caption in enumerate(captions)
        if idx not in used_caption_indexes and caption["page"] == image["page"]
    ]
    if same_page:
        idx, caption = same_page[0]
        used_caption_indexes.add(idx)
        return caption

    next_page = [
        (idx, caption)
        for idx, caption in enumerate(captions)
        if idx not in used_caption_indexes and caption["page"] == image["page"] + 1
    ]
    if next_page:
        idx, caption = next_page[0]
        used_caption_indexes.add(idx)
        return caption

    return None


def extract_figures(
    pdf_path: str,
    output_dir: str,
    min_width: int = 200,
    min_height: int = 200,
) -> List[Dict[str, Any]]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    try:
        captions = extract_caption_candidates(doc)
        images = collect_images(doc, min_width=min_width, min_height=min_height)

        figures: List[Dict[str, Any]] = []
        used_caption_indexes: set = set()
        for sequence, image in enumerate(images, start=1):
            caption = pick_caption(image, captions, used_caption_indexes)
            ext = image["ext"].lower()
            file_name = f"fig{sequence}.{ext}"
            file_path = output / file_name
            file_path.write_bytes(image["bytes"])

            figure = {
                "id": f"fig{sequence}",
                "number": sequence,
                "file": file_name,
                "file_path": f"figures/{file_name}",
                "page": image["page"],
                "size": f"{image['width']}x{image['height']}",
                "width": image["width"],
                "height": image["height"],
                "sha256": image["sha256"],
                "source_number": caption["source_number"] if caption else None,
                "caption": caption["caption"] if caption else "",
                "rect": image.get("rect"),
            }
            figures.append(figure)
            print(f"Extracted: {file_name} ({figure['size']}) from page {image['page']}")

        meta = {
            "schema_version": 2,
            "pdf_path": str(Path(pdf_path).resolve()),
            "min_width": min_width,
            "min_height": min_height,
            "figures": figures,
        }
        (output / "figures_meta.json").write_text(json.dumps(figures, ensure_ascii=False, indent=2), encoding="utf-8")
        (output / "figure_map.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\nTotal: {len(figures)} figures extracted to {output_dir}")
        print(f"Metadata saved to {output / 'figures_meta.json'}")
        print(f"Figure map saved to {output / 'figure_map.json'}")
        return figures
    finally:
        doc.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="从 PDF 提取论文图片")
    parser.add_argument("pdf_path", help="输入 PDF 路径")
    parser.add_argument("output_dir", help="图片输出目录")
    parser.add_argument("--min-width", type=int, default=200, help="最小图片宽度，默认 200")
    parser.add_argument("--min-height", type=int, default=200, help="最小图片高度，默认 200")
    args = parser.parse_args()

    if not Path(args.pdf_path).exists():
        print(f"Error: PDF file not found: {args.pdf_path}", file=sys.stderr)
        return 1

    extract_figures(args.pdf_path, args.output_dir, args.min_width, args.min_height)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
