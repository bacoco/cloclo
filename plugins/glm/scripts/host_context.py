#!/usr/bin/env python3
"""Export visible Codex or Claude conversation text for GLM."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any


CODEX_ROOTS = (Path.home() / ".codex" / "sessions", Path.home() / ".codex" / "archived_sessions")
CLAUDE_ROOT = Path.home() / ".claude" / "projects"
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


def _inside(path: Path, roots: tuple[Path, ...]) -> bool:
    for root in roots:
        try:
            path.relative_to(root.resolve())
            return True
        except ValueError:
            pass
    return False


def _explicit_source(value: str, roots: tuple[Path, ...], label: str) -> Path:
    candidate = Path(value).expanduser().resolve()
    if candidate.suffix != ".jsonl" or not candidate.is_file() or not _inside(candidate, roots):
        raise RuntimeError(f"{label} transcript must be a JSONL file inside its session directory.")
    return candidate


def find_codex_source(source: str | None = None, thread_id: str | None = None) -> Path:
    if source:
        return _explicit_source(source, CODEX_ROOTS, "Codex")
    requested = thread_id or os.environ.get("CODEX_THREAD_ID")
    if not requested:
        raise RuntimeError("Could not identify the current Codex thread. Pass --source or --thread-id.")
    candidates: list[Path] = []
    for root in CODEX_ROOTS:
        if root.exists():
            candidates.extend(root.rglob(f"*{requested}*.jsonl"))
    if not candidates:
        raise RuntimeError(f"Could not find the Codex transcript for thread {requested}.")
    return max(candidates, key=lambda path: path.stat().st_mtime).resolve()


def find_claude_source(source: str | None = None, session_id: str | None = None) -> Path:
    if source:
        return _explicit_source(source, (CLAUDE_ROOT,), "Claude")
    env_source = os.environ.get("GLM_COMPANION_CLAUDE_TRANSCRIPT") or os.environ.get("CODEX_COMPANION_TRANSCRIPT_PATH")
    if env_source:
        return _explicit_source(env_source, (CLAUDE_ROOT,), "Claude")
    requested = session_id or os.environ.get("GLM_COMPANION_CLAUDE_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID")
    if requested and CLAUDE_ROOT.exists():
        candidates = list(CLAUDE_ROOT.rglob(f"*{requested}*.jsonl"))
        if candidates:
            return max(candidates, key=lambda path: path.stat().st_mtime).resolve()
    raise RuntimeError("Could not identify the current Claude transcript. Pass --source.")


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return redact_secrets(content.strip())
    chunks: list[str] = []
    for block in content or []:
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        value = block.get("text")
        if isinstance(value, str) and value.strip():
            chunks.append(value.strip())
    return redact_secrets("\n".join(chunks))


def codex_messages(source: Path) -> list[dict[str, str]]:
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
            chunks: list[str] = []
            for block in payload.get("content") or []:
                if isinstance(block, dict):
                    value = block.get("text") or block.get("input_text") or block.get("output_text")
                    if isinstance(value, str) and value.strip():
                        chunks.append(value.strip())
            if chunks:
                messages.append({"role": str(payload["role"]), "text": redact_secrets("\n".join(chunks))})
    return messages


def claude_messages(source: Path) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    with source.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("type") not in {"user", "assistant"} or item.get("isMeta") or item.get("isSidechain"):
                continue
            payload = item.get("message") or {}
            role = payload.get("role") or item.get("type")
            if role not in {"user", "assistant"}:
                continue
            text = _content_text(payload.get("content"))
            if text:
                messages.append({"role": str(role), "text": text})
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


def render_context(host: str, source: Path, messages: list[dict[str, str]]) -> dict[str, Any]:
    selected = bounded_messages(messages)
    lines = [
        f"<{host}_visible_conversation>",
        f"Visible user/{host.title()} messages imported as context. Hidden instructions, private reasoning,",
        "tool calls/results, attachments, and secrets are intentionally excluded. The delegated task is authoritative.",
        "",
    ]
    for message in selected:
        label = "USER" if message["role"] == "user" else host.upper()
        lines.extend([f"[{label}]", message["text"], ""])
    lines.append(f"</{host}_visible_conversation>")
    return {"sourcePath": str(source), "messageCount": len(selected), "text": "\n".join(lines)}


def load_context(host: str, source: str | None = None, session_id: str | None = None) -> dict[str, Any]:
    if host == "codex":
        path = find_codex_source(source=source, thread_id=session_id)
        return render_context(host, path, codex_messages(path))
    if host == "claude":
        path = find_claude_source(source=source, session_id=session_id)
        return render_context(host, path, claude_messages(path))
    raise RuntimeError(f"Unsupported host: {host}")
