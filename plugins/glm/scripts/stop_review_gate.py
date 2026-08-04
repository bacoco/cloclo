#!/usr/bin/env python3
"""Optional fail-open GLM stop review gate for Codex and Claude."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True

from glm_runtime import setup_report
from glm_state import ACTIVE_STATUSES, get_config, list_jobs, workspace_root


ROOT = Path(__file__).resolve().parent.parent
COMPANION = ROOT / "scripts" / "glm_companion.py"
TEMPLATE = ROOT / "prompts" / "stop-review-gate.md"


def input_data() -> dict:
    try:
        value = json.loads(sys.stdin.read() or "{}")
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def detect_host(data: dict) -> str:
    transcript = str(data.get("transcript_path") or os.environ.get("GLM_COMPANION_CLAUDE_TRANSCRIPT") or "")
    return "claude" if "/.claude/projects/" in transcript else "codex"


def emit_block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


def main() -> int:
    data = input_data()
    if data.get("stop_hook_active") or data.get("stopHookActive") or os.environ.get("GLM_COMPANION_STOP_GATE_ACTIVE"):
        return 0
    host = detect_host(data)
    cwd = workspace_root(data.get("cwd") or os.getcwd())
    running = next((job for job in list_jobs(cwd, include_all=True) if job.get("status") in ACTIVE_STATUSES), None)
    running_note = f"GLM job {running['id']} is still running." if running else ""
    if not get_config(cwd).get(f"stopReviewGate{host.title()}"):
        if running_note:
            print(running_note, file=sys.stderr)
        return 0
    if not setup_report(cwd).get("ready"):
        print("GLM is unavailable; allowing stop. Run the GLM setup command.", file=sys.stderr)
        return 0
    prompt = TEMPLATE.read_text(encoding="utf-8").replace("{{HOST_RESPONSE}}", str(data.get("last_assistant_message") or ""))
    command = [
        sys.executable, str(COMPANION), "task", "--host", host, "--cwd", str(cwd), "--stop-gate",
        "--no-context", "--json", "--timeout-seconds", "840",
    ]
    try:
        result = subprocess.run(
            command, cwd=cwd, input=prompt, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=870, check=False, env={**os.environ, "GLM_COMPANION_STOP_GATE_ACTIVE": "1"},
        )
    except subprocess.TimeoutExpired:
        print("GLM stop review timed out; allowing stop.", file=sys.stderr)
        return 0
    if result.returncode != 0:
        print(f"GLM stop review failed; allowing stop: {result.stderr.strip() or 'unknown error'}", file=sys.stderr)
        return 0
    try:
        raw = str(json.loads(result.stdout).get("rawOutput") or "").strip()
    except (json.JSONDecodeError, AttributeError):
        print("GLM stop review returned invalid output; allowing stop.", file=sys.stderr)
        return 0
    first = raw.splitlines()[0].strip() if raw else ""
    if first.startswith("BLOCK:"):
        reason = first.removeprefix("BLOCK:").strip() or "GLM found a blocking issue."
        emit_block((running_note + " " + reason).strip())
    elif not first.startswith("ALLOW:"):
        print("GLM stop review returned an unexpected answer; allowing stop.", file=sys.stderr)
    elif running_note:
        print(running_note, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
