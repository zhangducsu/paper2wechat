#!/usr/bin/env python3
"""
PDF → content.json 确定性抽取脚本。

该脚本负责 P1 基线：文本、元信息、图片、figure map、run_state 一次性落盘，
后续 writer Agent 只消费结构化结果，不再临时拼接中间状态。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pdfplumber

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from extract_figures import extract_figures  # noqa: E402
from validate_run import validate_run  # noqa: E402


SECTION_ALIASES = {
    "abstract": {"abstract", "summary"},
    "introduction": {"introduction", "background"},
    "methods": {"methods", "materials and methods", "method", "experimental procedures"},
    "results": {"results", "findings"},
    "discussion": {"discussion"},
    "conclusion": {"conclusion", "conclusions", "interpretation"},
}

STOP_HEADINGS = {"references", "acknowledgments", "acknowledgements", "supplementary materials"}
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(20\d{2}|19\d{2})\b")
GENE_RE = re.compile(r"\b[A-Z][A-Z0-9-]{2,10}\b")
P_VALUE_RE = re.compile(r"\bP\s*[<=>]\s*0?\.\d+\b", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    root = path.resolve()
    for item in path.iterdir():
        resolved = item.resolve()
        if root not in resolved.parents and resolved != root:
            raise RuntimeError(f"Refuse to clean path outside target directory: {resolved}")
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)


def extract_pages(pdf_path: Path) -> List[Dict[str, Any]]:
    pages: List[Dict[str, Any]] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append({"page": index, "text": text})
    return pages


def write_full_text(pages: List[Dict[str, Any]], output_path: Path) -> None:
    chunks: List[str] = []
    for page in pages:
        chunks.append(f"=== PAGE {page['page']} ===")
        chunks.append(page["text"])
        chunks.append("")
    chunks.append(f"[Total pages: {len(pages)}]")
    output_path.write_text("\n".join(chunks), encoding="utf-8")


def normalize_heading(line: str) -> str:
    line = re.sub(r"^\d+\.?\s*", "", line.strip())
    line = re.sub(r"[:：]\s*$", "", line)
    return line.lower()


def heading_to_section(line: str) -> Optional[str]:
    normalized = normalize_heading(line)
    if normalized in STOP_HEADINGS:
        return "references"
    for section, aliases in SECTION_ALIASES.items():
        if normalized in aliases:
            return section
    return None


def parse_sections(full_text: str) -> Dict[str, str]:
    sections: Dict[str, List[str]] = {key: [] for key in SECTION_ALIASES}
    current: Optional[str] = None

    for raw_line in full_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("=== PAGE"):
            continue
        section = heading_to_section(line)
        if section == "references":
            current = None
            continue
        if section:
            current = section
            continue
        if current:
            sections[current].append(line)

    result = {key: "\n".join(value).strip() for key, value in sections.items()}

    if not result["abstract"]:
        first_page = full_text.split("=== PAGE 2 ===", 1)[0]
        start = re.search(r"\bBackground:\s*", first_page, re.IGNORECASE)
        end = re.search(r"\bIntroduction\b", first_page, re.IGNORECASE)
        if start:
            abstract_end = end.start() if end else len(first_page)
            result["abstract"] = " ".join(first_page[start.start() : abstract_end].split())

    compact_text = " ".join(full_text.split())
    if not any(result.values()):
        result["abstract"] = compact_text[:4000]

    return result


def extract_metadata(first_page_text: str, full_text: str) -> Dict[str, Any]:
    lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
    title_lines: List[str] = []
    capture_title = False
    for line in lines[:30]:
        if line.upper() in {"RESEARCH ARTICLE", "ARTICLE", "ORIGINAL ARTICLE"}:
            capture_title = True
            continue
        if capture_title:
            if line.startswith("Citation:") or DOI_RE.search(line):
                break
            if re.search(r"\d+\s*(Department|School|Institute|University)", line):
                break
            title_lines.append(line)
            if len(title_lines) >= 4:
                break

    title = " ".join(title_lines).strip()
    if not title and lines:
        title = lines[0]

    doi_match = DOI_RE.search(full_text)
    years = YEAR_RE.findall(first_page_text)

    return {
        "title": title,
        "authors": [],
        "journal": "",
        "year": int(years[-1]) if years else None,
        "doi": doi_match.group(0).rstrip(".") if doi_match else "",
    }


def extract_key_data(full_text: str) -> Dict[str, Any]:
    genes = sorted(set(GENE_RE.findall(full_text)))
    filtered_genes = [
        gene
        for gene in genes
        if gene not in {"DNA", "RNA", "PDF", "FIG", "PD", "SN"} and not gene.isdigit()
    ][:100]
    p_values = sorted(set(P_VALUE_RE.findall(full_text)))
    return {
        "genes": filtered_genes,
        "p_values": p_values,
        "metrics": {},
        "key_findings": [],
    }


def build_content(pdf_path: Path, output_dir: Path, min_width: int, min_height: int) -> Dict[str, Any]:
    figures_dir = output_dir / "figures"
    clean_directory(figures_dir)

    pages = extract_pages(pdf_path)
    full_text = "\n\n".join(f"=== PAGE {page['page']} ===\n{page['text']}" for page in pages)
    write_full_text(pages, output_dir / "full_text.txt")

    figures = extract_figures(str(pdf_path), str(figures_dir), min_width=min_width, min_height=min_height)
    content_figures = [
        {
            "id": figure["id"],
            "number": figure["number"],
            "caption": figure.get("caption", ""),
            "source_number": figure.get("source_number"),
            "file_path": figure["file_path"],
            "page": figure["page"],
            "size": figure["size"],
        }
        for figure in figures
    ]

    content = {
        "schema_version": 1,
        "source_pdf": str(pdf_path.resolve()),
        "page_count": len(pages),
        "metadata": extract_metadata(pages[0]["text"] if pages else "", full_text),
        "sections": parse_sections(full_text),
        "figures": content_figures,
        "key_data": extract_key_data(full_text),
    }
    return content


def main() -> int:
    parser = argparse.ArgumentParser(description="从 PDF 生成 paper2wechat content.json")
    parser.add_argument("pdf_path", help="输入 PDF 路径")
    parser.add_argument("--output-dir", default=".claude/tmp/extracted", help="输出目录")
    parser.add_argument("--min-width", type=int, default=200, help="最小图片宽度")
    parser.add_argument("--min-height", type=int, default=200, help="最小图片高度")
    parser.add_argument("--no-validate", action="store_true", help="跳过 content.json 校验")
    args = parser.parse_args()

    started_at = utc_now()
    pdf_path = Path(args.pdf_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_state_path = output_dir / "run_state.json"

    run_state: Dict[str, Any] = {
        "schema_version": 1,
        "status": "running",
        "started_at": started_at,
        "input_pdf": str(pdf_path),
        "output_dir": str(output_dir),
        "python_executable": sys.executable,
        "artifacts": {},
    }
    run_state_path.write_text(json.dumps(run_state, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

        content = build_content(pdf_path, output_dir, args.min_width, args.min_height)
        content_path = output_dir / "content.json"
        content_path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")

        validation = None
        if not args.no_validate:
            validation = validate_run(content_path=content_path, base_dir=output_dir)
            (output_dir / "validation.json").write_text(
                json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            if validation["status"] != "pass":
                raise RuntimeError("content.json 校验失败，详见 validation.json")

        run_state.update(
            {
                "status": "pass",
                "completed_at": utc_now(),
                "artifacts": {
                    "content_json": str(content_path),
                    "full_text": str(output_dir / "full_text.txt"),
                    "figures_dir": str(output_dir / "figures"),
                    "figure_map": str(output_dir / "figures" / "figure_map.json"),
                    "validation": str(output_dir / "validation.json") if validation else None,
                },
                "counts": {
                    "pages": content.get("page_count", 0),
                    "figures": len(content.get("figures", [])),
                },
                "validation": validation,
            }
        )
        print(json.dumps(run_state, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        run_state.update(
            {
                "status": "fail",
                "completed_at": utc_now(),
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        print(json.dumps(run_state, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    finally:
        run_state_path.write_text(json.dumps(run_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
