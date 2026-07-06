#!/usr/bin/env python3
"""
paper2wechat 质量门禁。

本地和 CI 使用同一入口，避免“本地跑一套、CI跑另一套”的漂移。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_step(name: str, command: List[str]) -> Dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return {
        "name": name,
        "command": command,
        "status": "pass" if result.returncode == 0 else "fail",
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def build_steps(skip_env: bool) -> List[Dict[str, Any]]:
    python = sys.executable
    qa_dir = ROOT / ".claude" / "tmp" / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)

    steps: List[Dict[str, Any]] = []
    if not skip_env:
        steps.append(
            run_step(
                "环境检查",
                [python, ".claude/scripts/check_env.py", "--json-output", ".claude/tmp/env_status.json"],
            )
        )

    steps.append(run_step("Python语法编译", [python, "-m", "compileall", ".claude/scripts", "tests"]))
    steps.append(run_step("单元测试", [python, "-m", "unittest", "discover", "-s", "tests", "-v"]))
    steps.append(
        run_step(
            "fixture渲染",
            [
                python,
                ".claude/scripts/md2wechat.py",
                "tests/fixtures/sample_article.md",
                "--output",
                ".claude/tmp/qa/sample_article.html",
                "--theme",
                "default",
                "--primary-color",
                "#20B2AA",
            ],
        )
    )
    steps.append(
        run_step(
            "fixture封面生成",
            [
                python,
                ".claude/scripts/generate_cover.py",
                "--article",
                "tests/fixtures/sample_article.md",
                "--figures-dir",
                "tests/fixtures/figures",
                # CI 不调用外部生图服务，只验证 AI 背景参数链路和报告字段。
                "--background",
                "tests/fixtures/figures/fig1.png",
                "--background-source",
                "ai_generated",
                "--require-ai-background",
                "--logo",
                ".claude/templates/references/global_assets/logo.jpg",
                "--output",
                ".claude/tmp/qa/sample_cover.png",
                "--square-output",
                ".claude/tmp/qa/sample_cover_square.png",
                "--json-output",
                ".claude/tmp/qa/cover_report.json",
            ],
        )
    )
    steps.append(
        run_step(
            "fixture产物校验",
            [
                python,
                ".claude/scripts/validate_run.py",
                "--content",
                "tests/fixtures/content.json",
                "--base-dir",
                "tests/fixtures",
                "--article",
                "tests/fixtures/sample_article.md",
                "--html",
                ".claude/tmp/qa/sample_article.html",
                "--output-dir",
                "tests/fixtures",
                "--cover",
                ".claude/tmp/qa/sample_cover.png",
                "--cover-report",
                ".claude/tmp/qa/cover_report.json",
                "--require-ai-cover",
                "--json-output",
                ".claude/tmp/qa/validation.json",
            ],
        )
    )
    return steps


def main() -> int:
    parser = argparse.ArgumentParser(description="运行 paper2wechat 质量门禁")
    parser.add_argument("--skip-env", action="store_true", help="跳过环境检查")
    parser.add_argument("--json-output", default=".claude/tmp/quality_report.json", help="质量报告输出路径")
    args = parser.parse_args()

    steps = build_steps(skip_env=args.skip_env)
    failed = [step for step in steps if step["status"] != "pass"]
    report = {
        "schema_version": 1,
        "checked_at": utc_now(),
        "status": "pass" if not failed else "fail",
        "python_executable": sys.executable,
        "steps": steps,
    }

    output_path = ROOT / args.json_output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({k: v for k, v in report.items() if k != "steps"}, ensure_ascii=False, indent=2))
    for step in steps:
        print(f"[{step['status']}] {step['name']}")
        if step["status"] != "pass":
            print(step["stdout"])
            print(step["stderr"], file=sys.stderr)

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
