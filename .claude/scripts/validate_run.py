#!/usr/bin/env python3
"""
paper2wechat 运行产物校验。

校验目标：
- content.json 的结构和图片元数据一致；
- Markdown/HTML 中的图片引用都能在对应输出目录找到；
- HTML 保持微信粘贴友好的基本约束。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image


MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
HTML_IMAGE_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", re.IGNORECASE)


def add_issue(issues: List[Dict[str, str]], level: str, code: str, message: str) -> None:
    issues.append({"level": level, "code": code, "message": message})


def resolve_relative(base_dir: Path, ref: str) -> Path:
    return (base_dir / ref).resolve()


def validate_content(content_path: Path, base_dir: Path) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    if not content_path.exists():
        add_issue(issues, "error", "content_missing", f"content.json 不存在: {content_path}")
        return issues

    try:
        content = json.loads(content_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        add_issue(issues, "error", "content_invalid_json", f"content.json 不是合法 JSON: {exc}")
        return issues

    metadata = content.get("metadata")
    if not isinstance(metadata, dict):
        add_issue(issues, "error", "metadata_missing", "content.json 缺少 metadata 对象")
    elif not metadata.get("title"):
        add_issue(issues, "warning", "metadata_title_missing", "metadata.title 为空")

    sections = content.get("sections")
    if not isinstance(sections, dict) or not sections:
        add_issue(issues, "error", "sections_missing", "content.json 缺少 sections 对象")

    figures = content.get("figures")
    if not isinstance(figures, list):
        add_issue(issues, "error", "figures_missing", "content.json 缺少 figures 数组")
        return issues

    seen_ids = set()
    seen_numbers = set()
    seen_paths = set()
    for index, figure in enumerate(figures):
        if not isinstance(figure, dict):
            add_issue(issues, "error", "figure_invalid", f"figures[{index}] 不是对象")
            continue

        figure_id = str(figure.get("id", ""))
        number = figure.get("number")
        file_path = str(figure.get("file_path", ""))

        if not figure_id:
            add_issue(issues, "error", "figure_id_missing", f"figures[{index}] 缺少 id")
        elif figure_id in seen_ids:
            add_issue(issues, "error", "figure_id_duplicate", f"重复 Figure id: {figure_id}")
        seen_ids.add(figure_id)

        if number in seen_numbers:
            add_issue(issues, "error", "figure_number_duplicate", f"重复 Figure number: {number}")
        seen_numbers.add(number)

        if not file_path:
            add_issue(issues, "error", "figure_path_missing", f"{figure_id or index} 缺少 file_path")
            continue
        if file_path in seen_paths:
            add_issue(issues, "error", "figure_path_duplicate", f"重复图片路径: {file_path}")
        seen_paths.add(file_path)

        if not resolve_relative(base_dir, file_path).exists():
            add_issue(issues, "error", "figure_file_missing", f"图片文件不存在: {file_path}")

    return issues


def validate_markdown(article_path: Path, base_dir: Path) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    if not article_path:
        return issues
    if not article_path.exists():
        add_issue(issues, "error", "article_missing", f"Markdown 文件不存在: {article_path}")
        return issues

    text = article_path.read_text(encoding="utf-8")
    article_base_dir = article_path.parent
    for ref in MD_IMAGE_RE.findall(text):
        if ref.startswith(("http://", "https://", "data:")):
            continue
        if not resolve_relative(article_base_dir, ref).exists():
            add_issue(issues, "error", "article_image_missing", f"Markdown 图片不存在: {ref}")

    return issues


def validate_html(html_path: Path, output_dir: Path) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    if not html_path:
        return issues
    if not html_path.exists():
        add_issue(issues, "error", "html_missing", f"HTML 文件不存在: {html_path}")
        return issues

    text = html_path.read_text(encoding="utf-8")
    lower = text.lower()
    if "<style" in lower:
        add_issue(issues, "error", "html_style_tag", "HTML 包含 <style> 标签")
    if " class=" in lower:
        add_issue(issues, "error", "html_class_attr", "HTML 包含 class 属性")
    if "<script" in lower:
        add_issue(issues, "error", "html_script_tag", "HTML 包含 <script> 标签")

    for ref in HTML_IMAGE_RE.findall(text):
        if ref.startswith(("http://", "https://", "data:")):
            continue
        if not resolve_relative(output_dir, ref).exists():
            add_issue(issues, "error", "html_image_missing", f"HTML 图片不存在: {ref}")

    return issues


def validate_cover(cover_path: Path, expected_size: str = "900x383") -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    if not cover_path.exists():
        add_issue(issues, "error", "cover_missing", f"封面文件不存在: {cover_path}")
        return issues

    try:
        with Image.open(cover_path) as image:
            actual_size = f"{image.width}x{image.height}"
    except Exception as exc:  # noqa: BLE001
        add_issue(issues, "error", "cover_invalid_image", f"封面不是可读取图片: {exc}")
        return issues

    if actual_size != expected_size:
        add_issue(issues, "error", "cover_size_mismatch", f"封面尺寸应为 {expected_size}，实际为 {actual_size}")
    return issues


def validate_cover_report(cover_report_path: Path, require_ai_cover: bool = False) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    if not cover_report_path.exists():
        add_issue(issues, "error", "cover_report_missing", f"封面报告不存在: {cover_report_path}")
        return issues

    try:
        report = json.loads(cover_report_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        add_issue(issues, "error", "cover_report_invalid_json", f"封面报告不是合法 JSON: {exc}")
        return issues

    if report.get("status") != "pass":
        add_issue(issues, "error", "cover_report_failed", "封面报告 status 不是 pass")
    if report.get("ai_watermark") is not False:
        add_issue(issues, "error", "cover_ai_watermark", "封面报告未确认 ai_watermark=false")
    if report.get("logo_watermark_applied") is not True:
        add_issue(issues, "error", "cover_logo_watermark_missing", "封面报告未确认 logo_watermark_applied=true")

    if require_ai_cover:
        if report.get("background_source") != "ai_generated":
            add_issue(issues, "error", "cover_background_not_ai", "封面背景来源不是 ai_generated")
        if report.get("ai_generated_background") is not True:
            add_issue(issues, "error", "cover_ai_background_missing", "封面报告未确认 ai_generated_background=true")

    return issues


def validate_run(
    content_path: Path,
    base_dir: Path,
    article_path: Optional[Path] = None,
    html_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    cover_path: Optional[Path] = None,
    cover_size: str = "900x383",
    cover_report_path: Optional[Path] = None,
    require_ai_cover: bool = False,
) -> Dict[str, Any]:
    issues: List[Dict[str, str]] = []
    issues.extend(validate_content(content_path, base_dir))
    if article_path:
        issues.extend(validate_markdown(article_path, base_dir))
    if html_path:
        issues.extend(validate_html(html_path, output_dir or html_path.parent))
    if cover_path:
        issues.extend(validate_cover(cover_path, cover_size))
    if cover_report_path:
        issues.extend(validate_cover_report(cover_report_path, require_ai_cover))

    errors = [issue for issue in issues if issue["level"] == "error"]
    warnings = [issue for issue in issues if issue["level"] == "warning"]
    return {
        "schema_version": 1,
        "status": "pass" if not errors else "fail",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 paper2wechat 运行产物")
    parser.add_argument("--content", default=".claude/tmp/extracted/content.json", help="content.json 路径")
    parser.add_argument("--base-dir", default=".claude/tmp/extracted", help="content/Markdown 图片相对目录")
    parser.add_argument("--article", help="可选：Markdown 文件路径")
    parser.add_argument("--html", help="可选：HTML 文件路径")
    parser.add_argument("--output-dir", default="output", help="HTML 图片相对目录")
    parser.add_argument("--cover", help="可选：封面图路径")
    parser.add_argument("--cover-size", default="900x383", help="封面尺寸要求")
    parser.add_argument("--cover-report", help="可选：封面生成报告 JSON 路径")
    parser.add_argument("--require-ai-cover", action="store_true", help="要求封面背景来源为 AI 生图")
    parser.add_argument("--json-output", help="可选：把校验结果写入 JSON")
    args = parser.parse_args()

    result = validate_run(
        content_path=Path(args.content),
        base_dir=Path(args.base_dir),
        article_path=Path(args.article) if args.article else None,
        html_path=Path(args.html) if args.html else None,
        output_dir=Path(args.output_dir),
        cover_path=Path(args.cover) if args.cover else None,
        cover_size=args.cover_size,
        cover_report_path=Path(args.cover_report) if args.cover_report else None,
        require_ai_cover=args.require_ai_cover,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)

    if args.json_output:
        output_path = Path(args.json_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")

    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
