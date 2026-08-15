#!/usr/bin/env python3
"""Run GLM through Claude Code's Anthropic-compatible transport."""

# PDG-LARGE-FILE-JUSTIFICATION: Provider authentication, CLI policy, OS sandbox,
# streaming protocol, timeouts, and normalized results form one security boundary.

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import threading
from typing import Any, Callable
import urllib.error
import urllib.request

from glm_state import state_root, workspace_root


ZAI_BASE_URL = "https://api.z.ai/api/anthropic"
ZAI_MODELS_URL = "https://api.z.ai/api/coding/paas/v4/models"
DEFAULT_MODEL = "glm-5.3"
FALLBACK_MODEL = "glm-4.7"
DEFAULT_HAIKU_MODEL = "glm-4.7"
DEPTH_ENV = "GLM_COMPANION_DEPTH"
READ_ONLY_TOOLS = "Read,Grep,Glob,Bash(git diff:*),Bash(git status:*),Bash(git log:*),Bash(git show:*),Bash(rg:*),Bash(ls:*)"
REQUIRED_FLAGS = {
    "--allowedTools", "--append-system-prompt", "--disable-slash-commands", "--effort",
    "--json-schema", "--max-budget-usd", "--model", "--output-format", "--permission-mode",
    "--resume", "--safe-mode", "--session-id", "--tools", "--verbose",
}
SYSTEM_PROMPT = """You are GLM acting as an independently delegated companion for Codex or Claude Code.
Complete the delegated task yourself in the current workspace. Never launch Codex, Claude Code, or this
GLM companion, and never delegate the work back. Treat imported conversation as context; the final task
is authoritative. Preserve unrelated changes. Obey read-only versus write-capable mode. Lead with the
outcome and include evidence, changed files, verification, uncertainties, and useful next steps.
"""
Progress = Callable[[dict[str, Any]], None]


def find_claude() -> str:
    executable = shutil.which("claude")
    if not executable:
        raise RuntimeError("Claude Code CLI is required as the GLM transport and is not on PATH.")
    return executable


def _env_value(path: Path, names: tuple[str, ...]) -> str | None:
    if not path.is_file():
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() in names:
            return value.strip().strip('"').strip("'") or None
    return None


def resolve_key(cwd: str | Path) -> tuple[str | None, str | None]:
    personal = Path.home() / ".glm.env"
    value = _env_value(personal, ("ZAI_API_KEY", "GLM_API_KEY"))
    if value:
        return value, f"file:{personal}"
    for name in ("ZAI_API_KEY", "GLM_API_KEY"):
        if os.environ.get(name):
            return os.environ[name], f"environment:{name}"
    root = workspace_root(cwd)
    value = _env_value(root / ".env", ("ZAI_API_KEY", "GLM_API_KEY"))
    return (value, f"file:{root / '.env'}") if value else (None, None)


def run_simple(command: list[str], cwd: str | Path, timeout: float = 15) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=Path(cwd).resolve(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)


def probe_provider(cwd: str | Path, model: str, timeout: float = 20) -> dict[str, Any]:
    key, _ = resolve_key(cwd)
    if not key:
        return {"reachable": False, "error": {"type": "missing_key", "message": "No Z.ai key configured."}}
    request = urllib.request.Request(
        ZAI_MODELS_URL, method="GET",
        headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
        available = {
            str(item.get("id"))
            for item in payload.get("data", [])
            if isinstance(item, dict) and item.get("id")
        }
        base_model = model.removesuffix("[1m]")
        warning = None
        if available and base_model not in available:
            warning = {
                "type": "model_not_listed",
                "message": f"Model {base_model} is absent from the provider catalog; a live call remains authoritative.",
            }
        return {"reachable": True, "error": None, "warning": warning}
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            payload = {"error": {"type": "http_error", "message": f"HTTP {exc.code}"}}
        return {"reachable": False, "error": payload.get("error") or payload}
    except (OSError, TimeoutError) as exc:
        return {"reachable": False, "error": {"type": "network_error", "message": str(exc)}}


def setup_report(cwd: str | Path, probe: bool = False) -> dict[str, Any]:
    executable = shutil.which("claude")
    key, key_source = resolve_key(cwd)
    report: dict[str, Any] = {
        "ready": False, "transport": executable, "transportVersion": None,
        "provider": "Z.ai", "endpoint": ZAI_BASE_URL, "model": os.environ.get("GLM_MODEL") or DEFAULT_MODEL,
        "fallbackModel": os.environ.get("GLM_FALLBACK_MODEL") or FALLBACK_MODEL,
        "keyConfigured": bool(key), "keySource": key_source,
    }
    if not executable:
        report["error"] = "Claude Code CLI is missing."
        return report
    version = run_simple([executable, "--version"], cwd)
    help_result = run_simple([executable, "--help"], cwd)
    missing = sorted(flag for flag in REQUIRED_FLAGS if flag not in help_result.stdout)
    report["transportVersion"] = version.stdout.strip() if version.returncode == 0 else None
    report["cliContract"] = {"compatible": help_result.returncode == 0 and not missing, "missingFlags": missing}
    report["configured"] = bool(key and report["transportVersion"] and report["cliContract"]["compatible"])
    report["providerProbe"] = probe_provider(cwd, str(report["model"])) if probe and report["configured"] else {"reachable": None, "error": None}
    report["ready"] = bool(report["configured"] and report["providerProbe"]["reachable"] is not False)
    return report


def provider_env(cwd: str | Path, model: str) -> dict[str, str]:
    key, _ = resolve_key(cwd)
    if not key:
        raise RuntimeError(
            "No Z.ai key found. Add it to ~/.glm.env, set ZAI_API_KEY or "
            "GLM_API_KEY, or add it to the workspace .env."
        )
    env = dict(os.environ)
    for name in (
        "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "ANTHROPIC_SMALL_FAST_MODEL",
        "CLAUDE_CODE_OAUTH_TOKEN",
    ):
        env.pop(name, None)
    env.update({
        "ANTHROPIC_BASE_URL": ZAI_BASE_URL,
        "ANTHROPIC_AUTH_TOKEN": key,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": model,
        "ANTHROPIC_DEFAULT_SONNET_MODEL": model,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": DEFAULT_HAIKU_MODEL,
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "API_TIMEOUT_MS": "3000000",
        DEPTH_ENV: "1",
    })
    if model.endswith("[1m]"):
        env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] = "1000000"
    else:
        env.pop("CLAUDE_CODE_AUTO_COMPACT_WINDOW", None)
    return env


def sandbox_command(command: list[str], request: dict[str, Any], write_capable: bool) -> list[str]:
    sandbox = shutil.which("sandbox-exec")
    if not sandbox:
        return command
    rules = ["(version 1)", "(allow default)"]
    codex = shutil.which("codex")
    if codex:
        escaped = str(Path(codex).resolve()).replace("\\", "\\\\").replace('"', '\\"')
        rules.append(f'(deny process-exec (literal "{escaped}"))')
    if not write_capable:
        for path in sorted({Path(request["cwd"]).resolve(), state_root().resolve()}, key=str):
            escaped = str(path).replace("\\", "\\\\").replace('"', '\\"')
            rules.append(f'(deny file-write* (subpath "{escaped}"))')
    return [sandbox, "-p", " ".join(rules), *command]


def build_command(request: dict[str, Any]) -> list[str]:
    write_capable = bool(request.get("write"))
    model = str(request.get("model") or os.environ.get("GLM_MODEL") or DEFAULT_MODEL)
    command = [
        find_claude(), "-p", "--output-format", "stream-json", "--verbose", "--safe-mode",
        "--disable-slash-commands", "--name", "GLM companion", "--model", model,
        "--permission-mode", "acceptEdits" if write_capable else "dontAsk",
        "--append-system-prompt", SYSTEM_PROMPT,
    ]
    if request.get("resume_session_id"):
        command.extend(["--resume", str(request["resume_session_id"])])
    elif request.get("session_id"):
        command.extend(["--session-id", str(request["session_id"])])
    if request.get("effort"):
        command.extend(["--effort", str(request["effort"])])
    if request.get("max_budget_usd") is not None:
        command.extend(["--max-budget-usd", str(request["max_budget_usd"])])
    if request.get("json_schema"):
        command.extend(["--json-schema", json.dumps(request["json_schema"], separators=(",", ":"))])
    if request.get("disable_tools"):
        command.extend(["--tools", ""])
    elif not write_capable:
        command.extend(["--allowedTools", READ_ONLY_TOOLS, "--disallowedTools", "Edit,Write,NotebookEdit"])
    return sandbox_command(command, request, write_capable)


def _blocks(event: dict[str, Any]) -> list[dict[str, Any]]:
    content = (event.get("message") or {}).get("content") or []
    return [block for block in content if isinstance(block, dict)]


def _structured(value: Any, raw: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    for candidate in (value, raw):
        if isinstance(candidate, str):
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
    return None


def _run_glm_once(request: dict[str, Any], progress: Progress | None = None) -> dict[str, Any]:
    if os.environ.get(DEPTH_ENV):
        raise RuntimeError("Recursive GLM delegation is blocked.")
    cwd = Path(request.get("cwd") or os.getcwd()).expanduser().resolve()
    prompt = str(request.get("prompt") or "").strip()
    if not cwd.is_dir() or not prompt:
        raise RuntimeError("A valid workspace and non-empty GLM prompt are required.")
    model = str(request.get("model") or os.environ.get("GLM_MODEL") or DEFAULT_MODEL)
    process = subprocess.Popen(
        build_command(request), cwd=cwd, env=provider_env(cwd, model), text=True,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1,
        start_new_session=not bool(request.get("background")),
    )
    if progress:
        progress({"phase": "starting", "message": "GLM process started.", "pid": process.pid})
    timed_out = False
    kill_timer: threading.Timer | None = None

    def force_kill() -> None:
        if process.poll() is None:
            try:
                process.kill() if request.get("background") else os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def stop_timeout() -> None:
        nonlocal timed_out, kill_timer
        timed_out = True
        try:
            process.terminate() if request.get("background") else os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        kill_timer = threading.Timer(2, force_kill)
        kill_timer.daemon = True
        kill_timer.start()

    timer = threading.Timer(float(request["timeout_seconds"]), stop_timeout) if request.get("timeout_seconds") else None
    if timer:
        timer.daemon = True
        timer.start()

    assert process.stdin is not None
    def feed() -> None:
        try:
            assert process.stdin is not None
            process.stdin.write(prompt)
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass
    feeder = threading.Thread(target=feed, daemon=True)
    feeder.start()
    assert process.stdout is not None
    final: dict[str, Any] = {}
    texts: list[str] = []
    touched: list[str] = []
    diagnostics: list[str] = []
    session_id: str | None = None
    event_count = 0
    retry_count = 0
    provider_error = ""
    try:
        for raw_line in process.stdout:
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                diagnostics.append(line)
                continue
            event_count += 1
            if event.get("session_id"):
                session_id = str(event["session_id"])
            if event.get("type") == "system" and event.get("subtype") == "api_retry":
                retry_count += 1
                provider_error = f"Z.ai provider error: {event.get('error') or 'API retry'} ({retry_count} retries)."
                if progress:
                    progress({"phase": "retrying", "message": provider_error})
                if retry_count >= 3:
                    try:
                        process.terminate() if request.get("background") else os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            elif event.get("type") == "assistant":
                for block in _blocks(event):
                    if block.get("type") == "text" and block.get("text"):
                        texts.append(str(block["text"]))
                    if block.get("type") == "tool_use":
                        name = str(block.get("name") or "tool")
                        value = block.get("input") or {}
                        path = value.get("file_path") or value.get("path")
                        if path and name.lower() in {"edit", "write", "notebookedit"}:
                            touched.append(str(path))
                        if progress:
                            progress({"phase": "editing" if name.lower() in {"edit", "write", "notebookedit"} else "investigating", "message": f"GLM tool: {name}"})
            elif event.get("type") == "result":
                final = event
                if progress:
                    progress({"phase": "finalizing", "message": "GLM returned a final result.", "sessionId": session_id})
    finally:
        returncode = process.wait()
        feeder.join(timeout=1)
        if timer:
            timer.cancel()
        if kill_timer:
            kill_timer.cancel()
    raw_output = str(final.get("result") or "").strip() or (texts[-1].strip() if texts else "")
    failed = timed_out or returncode != 0 or bool(final.get("is_error"))
    error = "GLM timed out." if timed_out else (provider_error or str(final.get("result") or "") or (diagnostics[-1] if diagnostics else "GLM exited without a result.")) if failed else ""
    return {
        "status": 1 if failed else 0, "returncode": returncode, "provider": "Z.ai", "model": model,
        "sessionId": session_id or final.get("session_id"), "rawOutput": raw_output,
        "structuredOutput": _structured(final.get("structured_output"), raw_output),
        "touchedFiles": sorted(set(touched)) if request.get("write") else [],
        "permissionDenials": final.get("permission_denials") or [], "usage": final.get("usage"),
        "modelUsage": final.get("modelUsage"), "totalCostUsd": final.get("total_cost_usd"),
        "durationMs": final.get("duration_ms"), "terminalReason": final.get("terminal_reason"),
        "stopReason": final.get("stop_reason"), "eventCount": event_count, "providerRetryCount": retry_count,
        "providerError": provider_error or None, "errorMessage": error,
    }


def run_glm(request: dict[str, Any], progress: Progress | None = None) -> dict[str, Any]:
    model = str(request.get("model") or os.environ.get("GLM_MODEL") or DEFAULT_MODEL)
    primary = _run_glm_once({**request, "model": model}, progress=progress)
    fallback = str(os.environ.get("GLM_FALLBACK_MODEL") or FALLBACK_MODEL)
    provider_failure = " ".join(
        str(primary.get(key) or "") for key in ("providerError", "errorMessage")
    ).lower()
    rate_limited = any(marker in provider_failure for marker in ("rate_limit", "rate limit", "rate-limit", "429", "1313"))
    should_fallback = (
        primary.get("status") != 0
        and int(primary.get("providerRetryCount") or 0) >= 3
        and rate_limited
        and model != fallback
    )
    if not should_fallback:
        return primary
    if progress:
        progress({
            "phase": "fallback",
            "message": f"{model} unavailable; retrying transparently with {fallback}.",
        })
    fallback_request = {**request, "model": fallback}
    if fallback_request.get("session_id"):
        fallback_request["session_id"] = None
    result = _run_glm_once(fallback_request, progress=progress)
    result["fallbackFrom"] = model
    result["primaryErrorMessage"] = primary.get("errorMessage")
    return result
