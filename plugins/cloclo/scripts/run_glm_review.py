#!/usr/bin/env python3
"""Adapt the canonical GLM companion result to CLoClo's review-file contract."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Sequence


ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "skills" / "glm-review" / "templates"
VERDICT = re.compile(r"verdict(?:\s+global)?\s*:\s*(PASS|CONCERNS|FAIL)", re.IGNORECASE)


def resolve_companion() -> list[str] | None:
    override = os.environ.get("GLM_COMPANION_BIN")
    if override:
        return [str(Path(override).expanduser())]
    executable = shutil.which("glm-companion")
    if executable:
        return [executable]

    sibling = ROOT.parent / "glm" / "scripts" / "glm_companion.py"
    if sibling.is_file():
        return [sys.executable, str(sibling)]

    config_root = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")).expanduser()
    preferred = list((config_root / "plugins" / "cache" / "cloclo" / "glm").glob("*/scripts/glm_companion.py"))
    candidates = preferred or list((config_root / "plugins" / "cache").glob("*/glm/*/scripts/glm_companion.py"))
    if candidates:
        newest = max(candidates, key=lambda path: path.stat().st_mtime)
        return [sys.executable, str(newest)]
    return None


def render_prompt(args: argparse.Namespace) -> str:
    template = (TEMPLATES / f"review-{args.review_type}-prompt.md").read_text(encoding="utf-8")
    values = {
        "{{SPEC_PATH}}": args.spec_path or "not provided",
        "{{PLAN_PATH}}": args.plan_path or "not provided",
        "{{BASE_REF}}": args.base_ref or "main",
        "{{COMMIT_LIST}}": args.commit_list or "derive from git history",
    }
    for marker, value in values.items():
        template = template.replace(marker, value)
    return (
        template
        + f"\n\nPipeline maturity: {args.maturity}."
        + (" Run the convergence-oriented pass." if args.iterate else " Run one independent pass.")
    )


def parse_result(stdout: str) -> dict:
    try:
        value = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("GLM companion returned invalid JSON.") from exc
    if not isinstance(value, dict):
        raise RuntimeError("GLM companion returned a non-object result.")
    return value


def run_review(args: argparse.Namespace, companion: str | None = None) -> int:
    command_prefix = [companion] if companion else resolve_companion()
    if not command_prefix:
        print("[glm-review] glm-companion is unavailable. Install/enable glm@cloclo.", file=sys.stderr)
        return 2

    cwd = Path(args.cwd).expanduser().resolve()
    output = Path(args.output_file).expanduser().resolve()
    runtime_log = Path(f"{output}.runtime.log")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)

    prompt_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", prefix="cloclo-glm-", delete=False) as handle:
            handle.write(render_prompt(args))
            prompt_path = Path(handle.name)
        command = [
            *command_prefix, "task", "--host", "claude", "--cwd", str(cwd), "--wait", "--fresh",
            "--no-context", "--json", "--timeout-seconds", str(args.timeout_seconds),
            "--prompt-file", str(prompt_path),
        ]
        completed = subprocess.run(
            command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=args.timeout_seconds + 30, check=False,
        )
        runtime_log.write_text(
            completed.stdout + (f"\n--- stderr ---\n{completed.stderr}" if completed.stderr else ""),
            encoding="utf-8",
        )
        if completed.returncode != 0:
            print(f"[glm-review] companion failed (exit={completed.returncode}); see {runtime_log}", file=sys.stderr)
            return 2
        result = parse_result(completed.stdout)
        review = str(result.get("rawOutput") or "").strip()
        if not review or not VERDICT.search(review):
            print(f"[glm-review] missing review verdict; see {runtime_log}", file=sys.stderr)
            return 2
        output.write_text(review + "\n", encoding="utf-8")
        model = result.get("model") or "unknown"
        fallback = f" fallback={result.get('fallbackFrom')}->{model}" if result.get("fallbackFrom") else ""
        print(f"[glm-review] OK engine={model}{fallback}: {output}")
        return 0
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        runtime_log.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        print(f"[glm-review] failed: {exc}; see {runtime_log}", file=sys.stderr)
        return 2
    finally:
        if prompt_path:
            prompt_path.unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--review-type", choices=("spec", "plan", "impl"), required=True)
    value.add_argument("--cwd", required=True)
    value.add_argument("--output-file", required=True)
    value.add_argument("--spec-path")
    value.add_argument("--plan-path")
    value.add_argument("--base-ref")
    value.add_argument("--commit-list")
    value.add_argument("--maturity", choices=("spike", "dev", "ship"), default="dev")
    value.add_argument("--iterate", action="store_true")
    value.add_argument("--timeout-seconds", type=int, default=900)
    return value


def main(argv: Sequence[str] | None = None) -> int:
    return run_review(parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
