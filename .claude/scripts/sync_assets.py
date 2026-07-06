#!/usr/bin/env python3
"""
同步全局素材到文章 figures 目录，并规范 Markdown 中的 global_assets 引用。
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path
from typing import List


GLOBAL_ASSET_RE = re.compile(r"\((global_assets/([^)]+))\)")


def copy_assets(source_dir: Path, figures_dir: Path) -> List[str]:
    copied: List[str] = []
    if not source_dir.exists():
        return copied

    figures_dir.mkdir(parents=True, exist_ok=True)
    for item in source_dir.iterdir():
        if not item.is_file():
            continue
        target = figures_dir / item.name
        shutil.copy2(item, target)
        copied.append(str(target))
    return copied


def normalize_article(article_path: Path) -> bool:
    if not article_path or not article_path.exists():
        return False

    text = article_path.read_text(encoding="utf-8")

    def replace(match: re.Match) -> str:
        filename = match.group(2)
        return f"(figures/{filename})"

    new_text = GLOBAL_ASSET_RE.sub(replace, text)
    if new_text == text:
        return False

    article_path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="同步 paper2wechat 全局素材")
    parser.add_argument("--source-dir", default=".claude/templates/references/global_assets", help="全局素材目录")
    parser.add_argument("--figures-dir", required=True, help="目标 figures 目录")
    parser.add_argument("--article", help="可选：需要规范图片引用的 Markdown 文件")
    args = parser.parse_args()

    copied = copy_assets(Path(args.source_dir), Path(args.figures_dir))
    changed = normalize_article(Path(args.article)) if args.article else False

    print(f"copied_assets={len(copied)}")
    for path in copied:
        print(path)
    print(f"article_normalized={str(changed).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
