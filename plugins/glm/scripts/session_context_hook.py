#!/usr/bin/env python3
"""Expose the current Claude transcript to the shared GLM runtime."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0
    transcript = str(data.get("transcript_path") or "").strip()
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if not transcript or not env_file:
        return 0
    source = Path(transcript).expanduser().resolve()
    root = (Path.home() / ".claude" / "projects").resolve()
    try:
        source.relative_to(root)
    except ValueError:
        return 0
    with Path(env_file).open("a", encoding="utf-8") as handle:
        handle.write(f"export GLM_COMPANION_CLAUDE_TRANSCRIPT={shell_quote(str(source))}\n")
        if data.get("session_id"):
            handle.write(f"export GLM_COMPANION_CLAUDE_SESSION_ID={shell_quote(str(data['session_id']))}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
