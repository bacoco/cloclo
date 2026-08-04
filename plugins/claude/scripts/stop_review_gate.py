#!/usr/bin/env python3
"""Optional Codex Stop hook backed by a read-only Claude review."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from claude_runtime import setup_report
from claude_state import ACTIVE_STATUSES, get_config, list_jobs, workspace_root


ROOT = Path(__file__).resolve().parent.parent
COMPANION = ROOT / "scripts" / "claude_companion.py"
TEMPLATE = ROOT / "prompts" / "stop-review-gate.md"


def hook_input() -> dict:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def emit_block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


def log_note(reason: str) -> None:
    print(reason, file=sys.stderr)


def main() -> int:
    data = hook_input()
    if data.get("stop_hook_active") or data.get("stopHookActive") or os.environ.get("CLAUDE_COMPANION_STOP_GATE_ACTIVE"):
        return 0
    cwd = workspace_root(data.get("cwd") or os.getcwd())
    running = next((job for job in list_jobs(cwd, include_all=True) if job.get("status") in ACTIVE_STATUSES), None)
    running_note = (
        f"Claude job {running['id']} is still running. Use `$claude status` or `$claude cancel {running['id']}`."
        if running else ""
    )
    if not get_config(cwd).get("stopReviewGate"):
        if running_note:
            print(running_note, file=sys.stderr)
        return 0
    if not setup_report(cwd).get("ready"):
        print("Claude is not ready for the stop review gate. Run `$claude setup`.", file=sys.stderr)
        return 0

    previous = str(data.get("last_assistant_message") or "").strip()
    prompt = TEMPLATE.read_text(encoding="utf-8").replace("{{CODEX_RESPONSE}}", previous)
    command = [
        sys.executable,
        str(COMPANION),
        "task",
        "--stop-gate",
        "--cwd",
        str(cwd),
        "--no-context",
        "--json",
        "--timeout-seconds",
        "840",
    ]
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            input=prompt,
            env={**os.environ, "CLAUDE_COMPANION_STOP_GATE_ACTIVE": "1"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=870,
            check=False,
        )
    except subprocess.TimeoutExpired:
        log_note("Claude stop-time review timed out; allowing stop. Run `$claude review --wait` manually if needed.")
        return 0
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        log_note(f"Claude stop-time review failed; allowing stop: {detail}")
        return 0
    try:
        payload = json.loads(result.stdout)
        raw = str(payload.get("rawOutput") or "").strip()
    except (json.JSONDecodeError, AttributeError):
        log_note("Claude stop-time review returned invalid output; allowing stop.")
        return 0
    first = raw.splitlines()[0].strip() if raw else ""
    if first.startswith("ALLOW:"):
        if running_note:
            print(running_note, file=sys.stderr)
        return 0
    if first.startswith("BLOCK:"):
        reason = first.removeprefix("BLOCK:").strip() or "Claude found unresolved material issues."
        emit_block((running_note + " " + reason).strip())
    else:
        log_note("Claude stop-time review returned an unexpected answer; allowing stop.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
