#!/usr/bin/env python3
"""
paper2wechat 环境检查脚本。

输出 JSON，必需项失败时返回非 0，便于 /paper2wechat 在正式运行前中止。
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


REQUIRED_MODULES = {
    "fitz": "PyMuPDF",
    "pdfplumber": "pdfplumber",
    "markdown": "markdown",
    "bs4": "beautifulsoup4",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def module_check(module_name: str, package_name: str) -> Dict[str, Any]:
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 - 需要暴露真实导入错误
        return {
            "name": package_name,
            "module": module_name,
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    version = getattr(module, "__version__", None)
    if module_name == "fitz":
        version = getattr(module, "version", version)
    return {
        "name": package_name,
        "module": module_name,
        "ok": True,
        "version": str(version),
    }


def is_windows_store_alias(path: Optional[str]) -> bool:
    if not path:
        return False
    p = Path(path)
    return "WindowsApps" in str(p) and (not p.exists() or p.stat().st_size == 0)


def writable_dir_check(path: Path) -> Dict[str, Any]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return {"path": str(path), "ok": True}
    except Exception as exc:  # noqa: BLE001 - 环境检查要报告具体失败
        return {"path": str(path), "ok": False, "error": f"{type(exc).__name__}: {exc}"}


def mcp_config_check(root: Path) -> Dict[str, Any]:
    candidates = [
        root / ".claude" / "mcp.json",
        Path.home() / ".claude" / "mcp.json",
    ]
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "Claude" / "claude_desktop_config.json")

    found: List[Dict[str, Any]] = []
    for path in candidates:
        if not path.exists():
            continue
        item: Dict[str, Any] = {"path": str(path), "ok": False}
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            servers = data.get("mcpServers", {})
            item["ok"] = "wechat-parser" in servers
            item["has_wechat_parser"] = "wechat-parser" in servers
        except Exception as exc:  # noqa: BLE001
            item["error"] = f"{type(exc).__name__}: {exc}"
        found.append(item)

    return {
        "ok": any(item.get("has_wechat_parser") for item in found),
        "required": False,
        "configs": found,
    }


def build_report() -> Dict[str, Any]:
    root = project_root()
    python_on_path = shutil.which("python")
    deps = [module_check(module, package) for module, package in REQUIRED_MODULES.items()]
    dirs = [
        writable_dir_check(root / ".claude" / "tmp"),
        writable_dir_check(root / "output"),
    ]

    required_checks_ok = (
        sys.version_info >= (3, 8)
        and not is_windows_store_alias(sys.executable)
        and all(item["ok"] for item in deps)
        and all(item["ok"] for item in dirs)
    )

    return {
        "schema_version": 1,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(root),
        "status": "pass" if required_checks_ok else "fail",
        "python": {
            "ok": sys.version_info >= (3, 8) and not is_windows_store_alias(sys.executable),
            "executable": sys.executable,
            "version": platform.python_version(),
            "python_on_path": python_on_path,
            "path_uses_windows_store_alias": is_windows_store_alias(python_on_path),
            "running_executable_is_windows_store_alias": is_windows_store_alias(sys.executable),
        },
        "dependencies": deps,
        "writable_dirs": dirs,
        "mcp_wechat_parser": mcp_config_check(root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 paper2wechat 运行环境")
    parser.add_argument("--json-output", help="可选：把检查结果写入指定 JSON 文件")
    args = parser.parse_args()

    report = build_report()
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)

    if args.json_output:
        output_path = Path(args.json_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")

    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
