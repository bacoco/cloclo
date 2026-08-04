#!/usr/bin/env python3
"""Claude Companion: delegate, review, transfer, track, and cancel Claude work from Codex."""

# PDG-LARGE-FILE-JUSTIFICATION: This is the single auditable CLI boundary exposed by the
# plugin. Argument routing, job lifecycle, rendering, and worker dispatch stay together so
# background and foreground behavior cannot drift across multiple command entry points.

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any
import uuid

from claude_runtime import run_claude, setup_report
from claude_state import (
    ACTIVE_STATUSES,
    FINISHED_STATUSES,
    append_log,
    cancel_job,
    create_job,
    generate_job_id,
    get_config,
    latest_task_session,
    list_jobs,
    now_iso,
    read_job,
    resolve_job,
    set_config,
    update_job,
    workspace_root,
)
from codex_context import load_current_context


ROOT = Path(__file__).resolve().parent.parent
REVIEW_SCHEMA = ROOT / "schemas" / "review-output.schema.json"
PROMPTS = ROOT / "prompts"
VALID_EFFORTS = ("low", "medium", "high", "xhigh", "max")


def shorten(text: str, limit: int = 96) -> str:
    normalized = " ".join(str(text or "").split())
    return normalized if len(normalized) <= limit else normalized[: limit - 3] + "..."


def read_prompt(args: argparse.Namespace, allow_empty: bool = False) -> str:
    if getattr(args, "prompt_file", None):
        value = Path(args.prompt_file).expanduser().read_text(encoding="utf-8")
    elif getattr(args, "prompt", None):
        value = " ".join(args.prompt)
    elif not sys.stdin.isatty():
        value = sys.stdin.read()
    else:
        value = ""
    value = value.strip()
    if not value and not allow_empty:
        raise RuntimeError("Provide a task prompt, --prompt-file, or piped stdin.")
    return value


def context_for_task(args: argparse.Namespace, is_resume: bool) -> dict[str, Any] | None:
    explicit = bool(
        getattr(args, "context_current", False)
        or getattr(args, "source", None)
        or getattr(args, "thread_id", None)
    )
    if getattr(args, "no_context", False):
        return None
    if is_resume and not explicit:
        return None
    try:
        return load_current_context(
            source=getattr(args, "source", None),
            thread_id=getattr(args, "thread_id", None),
        )
    except RuntimeError:
        if explicit:
            raise
        return None


def combine_context(context: dict[str, Any] | None, task: str) -> str:
    task_block = f"<delegated_task>\n{task}\n</delegated_task>"
    return f"{context['text']}\n\n{task_block}" if context else task_block


def git(cwd: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Git command failed.")
    return result.stdout.strip()


def default_branch(cwd: Path) -> str:
    remote = subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    if remote.returncode == 0 and remote.stdout.strip().startswith("refs/remotes/origin/"):
        return remote.stdout.strip().replace("refs/remotes/origin/", "", 1)
    for name in ("main", "master", "trunk"):
        check = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{name}"], cwd=cwd, check=False
        )
        if check.returncode == 0:
            return name
    raise RuntimeError("Unable to detect the default branch. Pass --base or --scope working-tree.")


def review_target(cwd: Path, scope: str, base: str | None) -> tuple[Path, str]:
    root = Path(git(cwd, "rev-parse", "--show-toplevel")).resolve()
    if base:
        return root, f"branch diff against {base} (`git diff {base}...HEAD`)"
    if scope == "working-tree":
        return root, "working tree changes (staged, unstaged, and untracked)"
    if scope == "branch":
        detected = default_branch(root)
        return root, f"branch diff against {detected} (`git diff {detected}...HEAD`)"
    if scope != "auto":
        raise RuntimeError('Unsupported scope. Use "auto", "working-tree", or "branch".')
    dirty = git(root, "status", "--short", "--untracked-files=all")
    if dirty:
        return root, "working tree changes (staged, unstaged, and untracked)"
    detected = default_branch(root)
    return root, f"branch diff against {detected} (`git diff {detected}...HEAD`)"


def load_template(name: str, replacements: dict[str, str]) -> str:
    value = (PROMPTS / name).read_text(encoding="utf-8")
    for key, replacement in replacements.items():
        value = value.replace("{{" + key + "}}", replacement)
    return value


def render_task(result: dict[str, Any], title: str) -> str:
    raw = str(result.get("rawOutput") or "").strip() or str(result.get("errorMessage") or "Claude returned no output.")
    lines = [f"# {title}", "", raw]
    if result.get("touchedFiles"):
        lines.extend(["", "Touched files:", *[f"- {path}" for path in result["touchedFiles"]]])
    if result.get("permissionDenials"):
        lines.extend(["", f"Permission denials: {len(result['permissionDenials'])}"])
    if result.get("sessionId"):
        lines.extend(["", f"Claude session: {result['sessionId']}"])
    return "\n".join(lines).rstrip() + "\n"


def render_review(result: dict[str, Any], title: str, target: str) -> str:
    parsed = result.get("structuredOutput")
    if not isinstance(parsed, dict):
        return render_task(result, title)
    lines = [f"# {title}", "", f"Target: {target}", f"Verdict: {parsed.get('verdict', 'unknown')}", "", str(parsed.get("summary") or "")]
    findings = parsed.get("findings") or []
    if findings:
        lines.extend(["", "## Findings"])
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        for finding in sorted(findings, key=lambda item: order.get(item.get("severity"), 9)):
            location = f"{finding.get('file')}:{finding.get('line_start')}"
            lines.extend(
                [
                    "",
                    f"### [{str(finding.get('severity', 'unknown')).upper()}] {finding.get('title', '')}",
                    f"Location: {location} · Confidence: {finding.get('confidence')}",
                    "",
                    str(finding.get("body") or ""),
                    "",
                    f"Recommendation: {finding.get('recommendation', '')}",
                ]
            )
    else:
        lines.extend(["", "No material findings."])
    if parsed.get("next_steps"):
        lines.extend(["", "## Next steps", *[f"- {step}" for step in parsed["next_steps"]]])
    if result.get("sessionId"):
        lines.extend(["", f"Claude session: {result['sessionId']}"])
    return "\n".join(lines).rstrip() + "\n"


def execute_request(request: dict[str, Any], progress=None) -> tuple[dict[str, Any], str]:
    result = run_claude(request, progress=progress)
    result["contextSource"] = request.get("contextSource")
    result["contextMessageCount"] = int(request.get("contextMessageCount") or 0)
    kind = request.get("kind")
    if kind in {"review", "adversarial-review"}:
        rendered = render_review(result, request["title"], request["target"])
    elif kind == "transfer":
        if result.get("status") == 0 and result.get("sessionId"):
            result["resumeCommand"] = f"claude --resume {result['sessionId']}"
            rendered = (
                "Transferred the visible Codex conversation into a resumable Claude session.\n"
                f"Visible messages transferred: {request.get('contextMessageCount', 0)}\n"
                f"Claude session ID: {result['sessionId']}\n"
                f"Resume in Claude: {result['resumeCommand']}\n"
            )
        else:
            result["resumeCommand"] = None
            rendered = render_task(result, request.get("title") or "Claude Transfer")
    else:
        rendered = render_task(result, request.get("title") or "Claude Task")
    return result, rendered


def run_tracked(job: dict[str, Any], request: dict[str, Any]) -> tuple[dict[str, Any], str]:
    cwd = Path(job["workspaceRoot"])
    job_id = str(job["id"])
    update_job(cwd, job_id, {"status": "running", "phase": "starting", "startedAt": now_iso(), "pid": os.getpid()})
    append_log(job.get("logFile"), f"Starting {job.get('title', 'Claude job')}.")

    def progress(event: dict[str, Any]) -> None:
        patch: dict[str, Any] = {}
        if event.get("phase"):
            patch["phase"] = event["phase"]
        if event.get("sessionId"):
            patch["claudeSessionId"] = event["sessionId"]
        if event.get("pid") and not job.get("background"):
            patch["pid"] = event["pid"]
        if patch:
            update_job(cwd, job_id, patch)
        if event.get("message"):
            append_log(job.get("logFile"), str(event["message"]))

    try:
        result, rendered = execute_request(request, progress=progress)
        if read_job(cwd, job_id).get("status") == "cancelled":
            return result, rendered
        status = "completed" if result.get("status") == 0 else "failed"
        stored = update_job(
            cwd,
            job_id,
            {
                "status": status,
                "phase": "done" if status == "completed" else "failed",
                "pid": None,
                "completedAt": now_iso(),
                "claudeSessionId": result.get("sessionId"),
                "result": result,
                "rendered": rendered,
                "summary": shorten(result.get("rawOutput") or result.get("errorMessage") or job.get("summary", "")),
            },
        )
        append_log(job.get("logFile"), f"Finished with status {status}.")
        return stored["result"], stored["rendered"]
    except Exception as exc:
        update_job(
            cwd,
            job_id,
            {"status": "failed", "phase": "failed", "pid": None, "completedAt": now_iso(), "errorMessage": str(exc)},
        )
        append_log(job.get("logFile"), f"Failed: {exc}")
        raise


def enqueue(cwd: Path, job: dict[str, Any]) -> dict[str, Any]:
    command = [sys.executable, str(Path(__file__).resolve()), "_worker", "--cwd", str(cwd), "--job-id", str(job["id"])]
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    update_job(cwd, str(job["id"]), {"pid": process.pid})
    append_log(job.get("logFile"), "Queued for background execution.")
    return read_job(cwd, str(job["id"]))


def launch(request: dict[str, Any], background: bool, wait: bool, json_output: bool) -> int:
    if background and wait:
        raise RuntimeError("Choose either --background or --wait, not both.")
    request = {**request, "background": background}
    cwd = Path(request["cwd"])
    prefix = "review" if request["jobClass"] == "review" else "task"
    job = create_job(
        cwd,
        {
            "id": generate_job_id(prefix),
            "kind": request["kind"],
            "kindLabel": request["kind"],
            "jobClass": request["jobClass"],
            "title": request["title"],
            "summary": request["summary"],
            "write": bool(request.get("write")),
            "background": background,
            "request": request,
        },
    )
    if background:
        queued = enqueue(cwd, job)
        payload = {"jobId": queued["id"], "status": queued["status"], "title": queued["title"], "summary": queued["summary"]}
        if json_output:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(f"{queued['title']} started in the background as {queued['id']}. Check `$claude status {queued['id']}`.")
        return 0
    result, rendered = run_tracked(job, request)
    print(json.dumps(result, indent=2, ensure_ascii=False) if json_output else rendered, end="\n" if json_output else "")
    return int(result.get("status") or 0)


def command_setup(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd or os.getcwd()).resolve()
    if args.enable_review_gate and args.disable_review_gate:
        raise RuntimeError("Choose either --enable-review-gate or --disable-review-gate.")
    actions: list[str] = []
    if args.enable_review_gate:
        set_config(cwd, "stopReviewGate", True)
        actions.append("Enabled stop-time Claude review gate.")
    if args.disable_review_gate:
        set_config(cwd, "stopReviewGate", False)
        actions.append("Disabled stop-time Claude review gate.")
    report = setup_report(cwd)
    report.update({"reviewGateEnabled": bool(get_config(cwd).get("stopReviewGate")), "actionsTaken": actions})
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Claude CLI: {'ready' if report['ready'] else 'not ready'}")
        print(f"Version: {report.get('version') or 'unknown'}")
        print(f"Authenticated: {'yes' if report['auth'].get('loggedIn') else 'no'}")
        print(f"Stop review gate: {'enabled' if report['reviewGateEnabled'] else 'disabled'}")
        for action in actions:
            print(action)
    return 0 if report["ready"] else 1


def command_task(args: argparse.Namespace) -> int:
    cwd = workspace_root(args.cwd or os.getcwd())
    resume_id = args.resume
    if args.resume_last:
        resume_id = latest_task_session(cwd)
        if not resume_id:
            raise RuntimeError("No previous resumable Claude task was found for this workspace.")
    prompt = read_prompt(args, allow_empty=bool(resume_id)) or "Continue the previous task from where you stopped."
    context = context_for_task(args, is_resume=bool(resume_id))
    is_stop_gate = bool(args.stop_gate)
    request = {
        "kind": "stop-gate" if is_stop_gate else "task",
        "jobClass": "gate" if is_stop_gate else "task",
        "title": "Claude Stop Gate Review" if is_stop_gate else ("Claude Resume" if resume_id else "Claude Task"),
        "summary": shorten(prompt),
        "cwd": str(cwd),
        "prompt": combine_context(context, prompt),
        "write": args.write,
        "resume_session_id": resume_id,
        "model": args.model,
        "effort": args.effort,
        "max_budget_usd": args.max_budget_usd,
        "timeout_seconds": args.timeout_seconds,
        "contextSource": context.get("sourcePath") if context else None,
        "contextMessageCount": context.get("messageCount") if context else 0,
    }
    return launch(request, background=args.background, wait=args.wait, json_output=args.json)


def command_review(args: argparse.Namespace, adversarial: bool) -> int:
    cwd, target = review_target(Path(args.cwd or os.getcwd()).resolve(), args.scope, args.base)
    focus = " ".join(args.focus).strip() or "No extra focus provided."
    kind = "adversarial-review" if adversarial else "review"
    template = "adversarial-review.md" if adversarial else "review.md"
    title = "Claude Adversarial Review" if adversarial else "Claude Review"
    request = {
        "kind": kind,
        "jobClass": "review",
        "title": title,
        "summary": target,
        "target": target,
        "cwd": str(cwd),
        "prompt": load_template(template, {"TARGET": target, "FOCUS": focus}),
        "write": False,
        "model": args.model,
        "effort": args.effort,
        "max_budget_usd": args.max_budget_usd,
        "timeout_seconds": args.timeout_seconds,
        "json_schema": json.loads(REVIEW_SCHEMA.read_text(encoding="utf-8")),
    }
    return launch(request, background=args.background, wait=args.wait, json_output=args.json)


def command_transfer(args: argparse.Namespace) -> int:
    cwd = workspace_root(args.cwd or os.getcwd())
    context = load_current_context(source=args.source, thread_id=args.thread_id)
    session_id = str(uuid.uuid4())
    prompt = (
        context["text"]
        + "\n\n<transfer_task>Import this visible Codex history as working context. "
          "Acknowledge the transfer briefly and wait for the next instruction.</transfer_task>"
    )
    request = {
        "kind": "transfer",
        "jobClass": "task",
        "title": "Claude Transfer",
        "summary": f"Transfer {context['messageCount']} visible Codex messages",
        "cwd": str(cwd),
        "prompt": prompt,
        "write": False,
        "session_id": session_id,
        "disable_tools": True,
        "model": args.model,
        "effort": args.effort,
        "max_budget_usd": args.max_budget_usd,
        "timeout_seconds": args.timeout_seconds,
        "contextSource": context["sourcePath"],
        "contextMessageCount": context["messageCount"],
    }
    return launch(request, background=args.background, wait=args.wait, json_output=args.json)


def progress_preview(path: str | None, limit: int = 4) -> list[str]:
    if not path or not Path(path).exists():
        return []
    return [line.strip() for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()][-limit:]


def elapsed(job: dict[str, Any]) -> str:
    start = job.get("startedAt") or job.get("createdAt")
    end = job.get("completedAt")
    try:
        start_value = dt.datetime.fromisoformat(start)
        end_value = dt.datetime.fromisoformat(end) if end else dt.datetime.now(dt.timezone.utc)
        seconds = max(0, int((end_value - start_value).total_seconds()))
        return f"{seconds // 60}m {seconds % 60}s" if seconds >= 60 else f"{seconds}s"
    except (TypeError, ValueError):
        return "unknown"


def command_status(args: argparse.Namespace) -> int:
    cwd = workspace_root(args.cwd or os.getcwd())
    if args.wait and not args.reference:
        raise RuntimeError("status --wait requires a job id.")
    if args.reference and args.wait:
        deadline = time.monotonic() + args.timeout_ms / 1000
        while True:
            job = resolve_job(cwd, args.reference)
            if job.get("status") not in ACTIVE_STATUSES or time.monotonic() >= deadline:
                break
            time.sleep(max(0.1, args.poll_interval_ms / 1000))
    if args.reference:
        job = resolve_job(cwd, args.reference)
        payload = {**job, "elapsed": elapsed(job), "progressPreview": progress_preview(job.get("logFile"))}
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(f"Job: {job['id']}\nStatus: {job.get('status')}\nPhase: {job.get('phase')}\nElapsed: {payload['elapsed']}")
            for line in payload["progressPreview"]:
                print(line)
        return 0
    jobs = list_jobs(cwd, include_all=args.all)
    payload = [{**job, "elapsed": elapsed(job), "progressPreview": progress_preview(job.get("logFile"))} for job in jobs]
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("| Job | Kind | Status | Phase | Elapsed | Summary |")
        print("|---|---|---|---|---|---|")
        for job in payload:
            print(f"| {job['id']} | {job.get('kindLabel')} | {job.get('status')} | {job.get('phase')} | {job['elapsed']} | {shorten(job.get('summary', ''), 60)} |")
    return 0


def command_result(args: argparse.Namespace) -> int:
    cwd = workspace_root(args.cwd or os.getcwd())
    job = resolve_job(cwd, args.reference, FINISHED_STATUSES)
    stored = read_job(cwd, str(job["id"]))
    if args.json:
        print(json.dumps(stored, indent=2, ensure_ascii=False))
    else:
        print(stored.get("rendered") or stored.get("errorMessage") or "No stored result.", end="")
    return 0 if stored.get("status") == "completed" else 1


def command_resume_candidate(args: argparse.Namespace) -> int:
    cwd = workspace_root(args.cwd or os.getcwd())
    session_id = latest_task_session(cwd)
    payload = {"available": bool(session_id), "claudeSessionId": session_id}
    print(json.dumps(payload, indent=2) if args.json else (f"Resumable Claude session: {session_id}" if session_id else "No resumable Claude session found."))
    return 0


def command_cancel(args: argparse.Namespace) -> int:
    cwd = workspace_root(args.cwd or os.getcwd())
    job = cancel_job(cwd, args.reference)
    print(json.dumps(job, indent=2, ensure_ascii=False) if args.json else f"Cancelled Claude job {job['id']}.")
    return 0


def command_worker(args: argparse.Namespace) -> int:
    cwd = workspace_root(args.cwd)
    job = read_job(cwd, args.job_id)
    if job.get("status") == "cancelled":
        return 0
    request = job.get("request")
    if not isinstance(request, dict):
        raise RuntimeError(f"Stored job {args.job_id} has no request payload.")
    result, _ = run_tracked(job, request)
    return int(result.get("status") or 0)


def common_runtime(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cwd")
    parser.add_argument("--model")
    parser.add_argument("--effort", choices=VALID_EFFORTS)
    parser.add_argument("--max-budget-usd", type=float)
    parser.add_argument("--timeout-seconds", type=float)
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--json", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    setup = commands.add_parser("setup")
    setup.add_argument("--cwd")
    setup.add_argument("--enable-review-gate", action="store_true")
    setup.add_argument("--disable-review-gate", action="store_true")
    setup.add_argument("--json", action="store_true")
    setup.set_defaults(handler=command_setup)

    task = commands.add_parser("task", aliases=["rescue"])
    common_runtime(task)
    task.add_argument("--write", action="store_true")
    resumes = task.add_mutually_exclusive_group()
    resumes.add_argument("--resume-last", action="store_true")
    resumes.add_argument("--resume", metavar="SESSION_ID")
    resumes.add_argument("--fresh", action="store_true")
    context = task.add_mutually_exclusive_group()
    context.add_argument("--context-current", action="store_true")
    context.add_argument("--no-context", action="store_true")
    task.add_argument("--source")
    task.add_argument("--thread-id")
    task.add_argument("--prompt-file")
    task.add_argument("--stop-gate", action="store_true", help=argparse.SUPPRESS)
    task.add_argument("prompt", nargs="*")
    task.set_defaults(handler=command_task)

    for name, adversarial in (("review", False), ("adversarial-review", True)):
        review = commands.add_parser(name)
        common_runtime(review)
        review.add_argument("--base")
        review.add_argument("--scope", choices=("auto", "working-tree", "branch"), default="auto")
        review.add_argument("focus", nargs="*")
        review.set_defaults(handler=lambda args, selected=adversarial: command_review(args, selected))

    transfer = commands.add_parser("transfer")
    common_runtime(transfer)
    transfer.add_argument("--source")
    transfer.add_argument("--thread-id")
    transfer.set_defaults(handler=command_transfer)

    status = commands.add_parser("status")
    status.add_argument("reference", nargs="?")
    status.add_argument("--cwd")
    status.add_argument("--wait", action="store_true")
    status.add_argument("--timeout-ms", type=int, default=240000)
    status.add_argument("--poll-interval-ms", type=int, default=2000)
    status.add_argument("--all", action="store_true")
    status.add_argument("--json", action="store_true")
    status.set_defaults(handler=command_status)

    result = commands.add_parser("result")
    result.add_argument("reference", nargs="?")
    result.add_argument("--cwd")
    result.add_argument("--json", action="store_true")
    result.set_defaults(handler=command_result)

    candidate = commands.add_parser("task-resume-candidate")
    candidate.add_argument("--cwd")
    candidate.add_argument("--json", action="store_true")
    candidate.set_defaults(handler=command_resume_candidate)

    cancel = commands.add_parser("cancel")
    cancel.add_argument("reference", nargs="?")
    cancel.add_argument("--cwd")
    cancel.add_argument("--json", action="store_true")
    cancel.set_defaults(handler=command_cancel)

    worker = commands.add_parser("_worker")
    worker.add_argument("--cwd", required=True)
    worker.add_argument("--job-id", required=True)
    worker.set_defaults(handler=command_worker)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return int(args.handler(args))
    except (RuntimeError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
