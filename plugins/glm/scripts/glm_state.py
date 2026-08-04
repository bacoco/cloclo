#!/usr/bin/env python3
"""Persistent, locked state for the cross-host GLM companion."""

# PDG-LARGE-FILE-JUSTIFICATION: Persistence, job resolution, cancellation, and
# per-host gate configuration share one atomic schema and must evolve together.

from __future__ import annotations

import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
from typing import Any, Iterator


STATE_VERSION = 1
MAX_JOBS = 50
ACTIVE_STATUSES = {"queued", "running"}
FINISHED_STATUSES = {"completed", "failed", "cancelled"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def workspace_root(cwd: str | Path) -> Path:
    resolved = Path(cwd).expanduser().resolve()
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=resolved, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else resolved


def state_root() -> Path:
    configured = os.environ.get("GLM_COMPANION_HOME") or os.environ.get("GLM_PLUGIN_DATA")
    return (Path(configured).expanduser().resolve() / "state") if configured else Path.home() / ".glm-companion" / "state"


def state_dir(cwd: str | Path) -> Path:
    root = workspace_root(cwd)
    slug = "".join(c if c.isalnum() or c in "._-" else "-" for c in root.name).strip("-") or "workspace"
    digest = hashlib.sha256(str(root).encode()).hexdigest()[:16]
    return state_root() / f"{slug}-{digest}"


def state_file(cwd: str | Path) -> Path:
    return state_dir(cwd) / "state.json"


def jobs_dir(cwd: str | Path) -> Path:
    return state_dir(cwd) / "jobs"


def job_file(cwd: str | Path, job_id: str) -> Path:
    return jobs_dir(cwd) / f"{job_id}.json"


def default_state() -> dict[str, Any]:
    return {"version": STATE_VERSION, "config": {"stopReviewGateCodex": False, "stopReviewGateClaude": False}, "jobs": []}


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


@contextlib.contextmanager
def locked(cwd: str | Path) -> Iterator[None]:
    directory = state_dir(cwd)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".lock").open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def load_state(cwd: str | Path) -> dict[str, Any]:
    value = read_json(state_file(cwd)) or default_state()
    return {
        "version": STATE_VERSION,
        "config": {**default_state()["config"], **(value.get("config") or {})},
        "jobs": value.get("jobs") if isinstance(value.get("jobs"), list) else [],
    }


def save_state(cwd: str | Path, value: dict[str, Any]) -> None:
    jobs = sorted(value.get("jobs") or [], key=lambda item: str(item.get("updatedAt", "")), reverse=True)
    active = [job for job in jobs if job.get("status") in ACTIVE_STATUSES]
    finished = [job for job in jobs if job.get("status") not in ACTIVE_STATUSES]
    retained = active + finished[:max(0, MAX_JOBS - len(active))]
    retained.sort(key=lambda item: str(item.get("updatedAt", "")), reverse=True)
    retained_ids = {str(job.get("id")) for job in retained}
    for artifact in jobs_dir(cwd).glob("*"):
        if artifact.suffix not in {".json", ".log"}:
            continue
        job_id = artifact.stem
        if job_id in retained_ids or not re.fullmatch(r"[A-Za-z0-9._-]+", job_id):
            continue
        try:
            artifact.unlink(missing_ok=True)
        except OSError:
            pass
    atomic_json(state_file(cwd), {"version": STATE_VERSION, "config": value.get("config") or {}, "jobs": retained})


def get_config(cwd: str | Path) -> dict[str, Any]:
    return load_state(cwd)["config"]


def set_config(cwd: str | Path, key: str, value: Any) -> dict[str, Any]:
    with locked(cwd):
        state = load_state(cwd)
        state["config"][key] = value
        save_state(cwd, state)
        return state["config"]


def generate_job_id(prefix: str) -> str:
    stamp = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
    return f"{prefix}-{stamp:x}-{hashlib.sha256(os.urandom(16)).hexdigest()[:6]}"


def append_log(path: str | Path | None, message: str) -> None:
    if not path or not str(message).strip():
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(f"[{now_iso()}] {str(message).strip()}\n")


def create_job(cwd: str | Path, job: dict[str, Any]) -> dict[str, Any]:
    timestamp = now_iso()
    record = {
        "createdAt": timestamp, "updatedAt": timestamp, "status": "queued", "phase": "queued",
        "workspaceRoot": str(workspace_root(cwd)), **job,
    }
    record.setdefault("logFile", str(jobs_dir(cwd) / f"{record['id']}.log"))
    Path(record["logFile"]).parent.mkdir(parents=True, exist_ok=True)
    Path(record["logFile"]).write_text("", encoding="utf-8")
    with locked(cwd):
        atomic_json(job_file(cwd, record["id"]), record)
        state = load_state(cwd)
        state["jobs"] = [record] + [x for x in state["jobs"] if x.get("id") != record["id"]]
        save_state(cwd, state)
    return record


def update_job(cwd: str | Path, job_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    with locked(cwd):
        state = load_state(cwd)
        stored = read_json(job_file(cwd, job_id)) or next((x for x in state["jobs"] if x.get("id") == job_id), {"id": job_id})
        updated = {**stored, **patch, "id": job_id, "updatedAt": now_iso()}
        atomic_json(job_file(cwd, job_id), updated)
        keys = (
            "id", "host", "kind", "jobClass", "title", "summary", "status", "phase", "workspaceRoot",
            "write", "background", "pid", "glmSessionId", "createdAt", "startedAt", "completedAt",
            "updatedAt", "logFile", "errorMessage",
        )
        summary = {key: updated.get(key) for key in keys if updated.get(key) is not None}
        state["jobs"] = [summary] + [x for x in state["jobs"] if x.get("id") != job_id]
        save_state(cwd, state)
        return updated


def process_alive(pid: Any) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def refresh_stale_jobs(cwd: str | Path) -> None:
    for job in load_state(cwd)["jobs"]:
        if job.get("status") in ACTIVE_STATUSES and job.get("pid") and not process_alive(job.get("pid")):
            detail = read_json(job_file(cwd, str(job["id"]))) or job
            if detail.get("status") in ACTIVE_STATUSES:
                update_job(cwd, str(job["id"]), {"status": "failed", "phase": "failed", "pid": None, "completedAt": now_iso(), "errorMessage": "Worker exited without recording a result."})


def list_jobs(cwd: str | Path, include_all: bool = False) -> list[dict[str, Any]]:
    refresh_stale_jobs(cwd)
    jobs = sorted(load_state(cwd)["jobs"], key=lambda x: str(x.get("updatedAt", "")), reverse=True)
    return jobs if include_all else jobs[:8]


def resolve_job(cwd: str | Path, reference: str | None, statuses: set[str] | None = None) -> dict[str, Any]:
    jobs = list_jobs(cwd, include_all=True)
    if statuses:
        jobs = [x for x in jobs if x.get("status") in statuses]
    if not reference:
        if not jobs:
            raise RuntimeError("No matching GLM jobs found for this workspace.")
        return jobs[0]
    exact = [x for x in jobs if x.get("id") == reference]
    matches = exact or [x for x in jobs if str(x.get("id", "")).startswith(reference)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise RuntimeError(f'Ambiguous GLM job reference "{reference}".')
    raise RuntimeError(f'No GLM job found for "{reference}".')


def read_job(cwd: str | Path, job_id: str) -> dict[str, Any]:
    value = read_json(job_file(cwd, job_id))
    if not value:
        raise RuntimeError(f"Stored GLM job {job_id} is missing.")
    return value


def latest_task_session(cwd: str | Path, host: str) -> str | None:
    for job in list_jobs(cwd, include_all=True):
        if job.get("host") == host and job.get("jobClass") == "task" and job.get("kind") == "task" and job.get("glmSessionId") and job.get("status") in FINISHED_STATUSES:
            return str(job["glmSessionId"])
    return None


def cancel_job(cwd: str | Path, reference: str | None) -> dict[str, Any]:
    job = resolve_job(cwd, reference, ACTIVE_STATUSES)
    pid = job.get("pid")
    if pid and process_alive(pid):
        try:
            os.killpg(int(pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            try:
                os.kill(int(pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
    append_log(job.get("logFile"), "Cancelled by user.")
    return update_job(cwd, str(job["id"]), {"status": "cancelled", "phase": "cancelled", "pid": None, "completedAt": now_iso(), "errorMessage": "Cancelled by user."})
