#!/usr/bin/env python3
"""Export visible Codex turn history for a delegated Claude session."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any


ALLOWED_ROOTS = (Path.home() / ".codex" / "sessions", Path.home() / ".codex" / "archived_sessions")
MAX_CONTEXT_CHARS = 120_000
MAX_MESSAGES = 80
SECRET_PATTERNS = (
    re.compile(r"\b[0-9a-fA-F]{32}\.[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"(?i)\bAuthorization\s*:\s*Bearer\s+\S+"),
)


def redact_secrets(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    return redacted


def _inside_allowed_root(path: Path) -> bool:
    for root in ALLOWED_ROOTS:
        try:
            path.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def find_codex_session(source: str | None = None, thread_id: str | None = None) -> Path:
    if source:
        candidate = Path(source).expanduser().resolve()
        if candidate.suffix != ".jsonl" or not candidate.is_file() or not _inside_allowed_root(candidate):
            raise RuntimeError("Codex transcript source must be a JSONL file under ~/.codex/sessions or archived_sessions.")
        return candidate

    requested_id = thread_id or os.environ.get("CODEX_THREAD_ID")
    if not requested_id:
        raise RuntimeError("Could not identify the current Codex thread. Pass --source or --thread-id.")

    candidates: list[Path] = []
    for root in ALLOWED_ROOTS:
        if not root.exists():
            continue
        candidates.extend(root.rglob(f"*{requested_id}*.jsonl"))
    if candidates:
        return max(candidates, key=lambda path: path.stat().st_mtime)
    raise RuntimeError(f"Could not find the Codex transcript for thread {requested_id}.")


def _message_text(payload: dict[str, Any]) -> str:
    chunks: list[str] = []
    for block in payload.get("content") or []:
        if not isinstance(block, dict):
            continue
        value = block.get("text") or block.get("input_text") or block.get("output_text")
        if isinstance(value, str) and value.strip():
            chunks.append(value.strip())
    return redact_secrets("\n".join(chunks))


def visible_messages(source: Path) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    with source.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("type") != "response_item":
                continue
            payload = item.get("payload") or {}
            if payload.get("type") != "message" or payload.get("role") not in {"user", "assistant"}:
                continue
            text = _message_text(payload)
            if text:
                messages.append({"role": str(payload["role"]), "text": text})
    return messages


def bounded_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    size = 0
    for message in reversed(messages[-MAX_MESSAGES:]):
        cost = len(message["text"]) + 32
        if size + cost > MAX_CONTEXT_CHARS:
            if selected:
                break
            available = max(0, MAX_CONTEXT_CHARS - 32)
            marker = "[...earlier content in this message truncated...]\n"
            text = message["text"]
            if len(text) > available:
                tail_size = max(0, available - len(marker))
                text = (marker + text[-tail_size:]) if tail_size else text[-available:]
            message = {**message, "text": text}
            cost = len(text) + 32
        selected.append(message)
        size += cost
    return list(reversed(selected))


def render_visible_context(source: Path) -> tuple[str, int]:
    messages = bounded_messages(visible_messages(source))
    lines = [
        "<codex_visible_conversation>",
        "This is visible user/Codex turn history imported as context. Hidden system/developer instructions,",
        "private reasoning, and raw tool traces are intentionally excluded. The delegated task after this block",
        "is the active instruction.",
        "",
    ]
    for message in messages:
        label = "USER" if message["role"] == "user" else "CODEX"
        lines.extend([f"[{label}]", message["text"], ""])
    lines.append("</codex_visible_conversation>")
    return "\n".join(lines), len(messages)


def load_current_context(source: str | None = None, thread_id: str | None = None) -> dict[str, Any]:
    path = find_codex_session(source=source, thread_id=thread_id)
    text, count = render_visible_context(path)
    return {"sourcePath": str(path), "messageCount": count, "text": text}
