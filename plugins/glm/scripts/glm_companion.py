#!/usr/bin/env python3
"""Cross-host GLM companion: tasks, reviews, transfers, jobs, and gates."""

# PDG-LARGE-FILE-JUSTIFICATION: This is the single public CLI contract used by
# both Codex and Claude; keeping routing and lifecycle together prevents parity drift.

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Any
import uuid

sys.dont_write_bytecode = True

from glm_runtime import FALLBACK_MODEL, run_glm, setup_report
from glm_state import (
    ACTIVE_STATUSES, FINISHED_STATUSES, append_log, cancel_job, create_job, generate_job_id,
    get_config, latest_task_session, list_jobs, now_iso, read_job, resolve_job, set_config,
    update_job, workspace_root,
)
from host_context import load_context


ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
REVIEW_SCHEMA = ROOT / "schemas" / "review-output.schema.json"
VALID_EFFORTS = ("low", "medium", "high", "xhigh", "max")


def shorten(value: str, limit: int = 96) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


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
        raise RuntimeError("Provide a GLM task, --prompt-file, or piped stdin.")
    return value


def task_context(args: argparse.Namespace, resumed: bool) -> dict[str, Any] | None:
    explicit = bool(args.context_current or args.source or args.session_id)
    if args.no_context or (resumed and not explicit):
        return None
    try:
        return load_context(args.host, source=args.source, session_id=args.session_id)
    except RuntimeError:
        if explicit:
            raise
        return None


def combine_context(context: dict[str, Any] | None, task: str) -> str:
    block = f"<delegated_task>\n{task}\n</delegated_task>"
    return f"{context['text']}\n\n{block}" if context else block


def git(cwd: Path, *arguments: str) -> str:
    result = subprocess.run(["git", *arguments], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Git command failed.")
    return result.stdout.strip()


def default_branch(cwd: Path) -> str:
    remote = subprocess.run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    if remote.returncode == 0 and remote.stdout.strip().startswith("refs/remotes/origin/"):
        return remote.stdout.strip().replace("refs/remotes/origin/", "", 1)
    for name in ("main", "master", "trunk"):
        if subprocess.run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{name}"], cwd=cwd, check=False).returncode == 0:
            return name
    raise RuntimeError("Unable to detect the default branch. Pass --base or use --scope working-tree.")


def review_target(cwd: Path, scope: str, base: str | None) -> tuple[Path, str]:
    root = Path(git(cwd, "rev-parse", "--show-toplevel")).resolve()
    if base:
        return root, f"branch diff against {base} (`git diff {base}...HEAD`)"
    if scope == "working-tree":
        return root, "working tree changes (staged, unstaged, and untracked)"
    if scope == "branch":
        branch = default_branch(root)
        return root, f"branch diff against {branch} (`git diff {branch}...HEAD`)"
    if git(root, "status", "--short", "--untracked-files=all"):
        return root, "working tree changes (staged, unstaged, and untracked)"
    branch = default_branch(root)
    return root, f"branch diff against {branch} (`git diff {branch}...HEAD`)"


def template(name: str, replacements: dict[str, str]) -> str:
    value = (PROMPTS / name).read_text(encoding="utf-8")
    for key, replacement in replacements.items():
        value = value.replace("{{" + key + "}}", replacement)
    return value


def render_task(result: dict[str, Any], title: str) -> str:
    raw = str(result.get("rawOutput") or result.get("errorMessage") or "GLM returned no output.").strip()
    lines = [f"# {title}", "", raw]
    if result.get("fallbackFrom"):
        lines.extend(["", f"Model fallback: {result['fallbackFrom']} → {result.get('model')}"])
    if result.get("touchedFiles"):
        lines.extend(["", "Touched files:", *[f"- {path}" for path in result["touchedFiles"]]])
    if result.get("permissionDenials"):
        lines.extend(["", f"Permission denials: {len(result['permissionDenials'])}"])
    if result.get("sessionId"):
        lines.extend(["", f"GLM session: {result['sessionId']}"])
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
            lines.extend([
                "", f"### [{str(finding.get('severity', 'unknown')).upper()}] {finding.get('title', '')}",
                f"Location: {finding.get('file')}:{finding.get('line_start')} · Confidence: {finding.get('confidence')}",
                "", str(finding.get("body") or ""), "", f"Recommendation: {finding.get('recommendation', '')}",
            ])
    else:
        lines.extend(["", "No material findings."])
    if parsed.get("next_steps"):
        lines.extend(["", "## Next steps", *[f"- {step}" for step in parsed["next_steps"]]])
    if result.get("sessionId"):
        lines.extend(["", f"GLM session: {result['sessionId']}"])
    return "\n".join(lines).rstrip() + "\n"


def execute_request(request: dict[str, Any], progress=None) -> tuple[dict[str, Any], str]:
    result = run_glm(request, progress=progress)
    result["contextSource"] = request.get("contextSource")
    result["contextMessageCount"] = int(request.get("contextMessageCount") or 0)
    successful_session = result.get("status") == 0 and result.get("sessionId")
    companion = shlex.quote(str(ROOT / "bin" / "glm-companion"))
    result["resumeCommand"] = (
        f"{companion} task --host {request['host']} --resume {result['sessionId']}"
        if successful_session else None
    )
    if request["kind"] in {"review", "adversarial-review"}:
        rendered = render_review(result, request["title"], request["target"])
    elif request["kind"] == "transfer" and successful_session:
        rendered = (
            f"Transferred {request.get('contextMessageCount', 0)} visible {request['host'].title()} messages into GLM.\n"
            f"GLM session ID: {result['sessionId']}\nResume through the companion with `{result['resumeCommand']}`.\n"
        )
    else:
        rendered = render_task(result, request["title"])
    return result, rendered


def run_tracked(job: dict[str, Any], request: dict[str, Any]) -> tuple[dict[str, Any], str]:
    cwd = Path(job["workspaceRoot"])
    job_id = str(job["id"])
    update_job(cwd, job_id, {"status": "running", "phase": "starting", "startedAt": now_iso(), "pid": os.getpid()})
    append_log(job.get("logFile"), f"Starting {job['title']}.")

    def progress(event: dict[str, Any]) -> None:
        patch: dict[str, Any] = {}
        if event.get("phase"):
            patch["phase"] = event["phase"]
        if event.get("sessionId"):
            patch["glmSessionId"] = event["sessionId"]
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
        stored = update_job(cwd, job_id, {
            "status": status, "phase": "done" if status == "completed" else "failed", "pid": None,
            "completedAt": now_iso(), "glmSessionId": result.get("sessionId"), "result": result,
            "rendered": rendered, "summary": shorten(result.get("rawOutput") or result.get("errorMessage") or job.get("summary", "")),
        })
        append_log(job.get("logFile"), f"Finished with status {status}.")
        return stored["result"], stored["rendered"]
    except Exception as exc:
        update_job(cwd, job_id, {"status": "failed", "phase": "failed", "pid": None, "completedAt": now_iso(), "errorMessage": str(exc)})
        append_log(job.get("logFile"), f"Failed: {exc}")
        raise


def enqueue(cwd: Path, job: dict[str, Any]) -> dict[str, Any]:
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "_worker", "--cwd", str(cwd), "--job-id", str(job["id"])],
        cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    update_job(cwd, str(job["id"]), {"pid": process.pid})
    append_log(job.get("logFile"), "Queued for background execution.")
    return read_job(cwd, str(job["id"]))


def launch(request: dict[str, Any], background: bool, wait: bool, json_output: bool) -> int:
    if background and wait:
        raise RuntimeError("Choose either --background or --wait, not both.")
    request = {**request, "background": background}
    cwd = Path(request["cwd"])
    job = create_job(cwd, {
        "id": generate_job_id("review" if request["jobClass"] == "review" else "task"),
        "host": request["host"], "kind": request["kind"], "jobClass": request["jobClass"],
        "title": request["title"], "summary": request["summary"], "write": bool(request.get("write")),
        "background": background, "request": request,
    })
    if background:
        queued = enqueue(cwd, job)
        payload = {"jobId": queued["id"], "status": queued["status"], "title": queued["title"], "summary": queued["summary"]}
        print(json.dumps(payload, indent=2, ensure_ascii=False) if json_output else f"{queued['title']} started as {queued['id']}. Use `glm status {queued['id']}`.")
        return 0
    result, rendered = run_tracked(job, request)
    print(json.dumps(result, indent=2, ensure_ascii=False) if json_output else rendered, end="\n" if json_output else "")
    return int(result.get("status") or 0)


def command_setup(args: argparse.Namespace) -> int:
    cwd = workspace_root(args.cwd or os.getcwd())
    if args.enable_review_gate and args.disable_review_gate:
        raise RuntimeError("Choose either --enable-review-gate or --disable-review-gate.")
    key = f"stopReviewGate{args.host.title()}"
    if args.enable_review_gate:
        set_config(cwd, key, True)
    if args.disable_review_gate:
        set_config(cwd, key, False)
    report = setup_report(cwd, probe=not args.no_probe)
    report.update({"host": args.host, "reviewGateEnabled": bool(get_config(cwd).get(key))})
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        probe = report.get("providerProbe") or {}
        error = probe.get("error") or {}
        if probe.get("reachable") is True:
            probe_line = "Provider probe: reachable"
        elif probe.get("reachable") is False:
            identity = "/".join(str(value) for value in (error.get("type"), error.get("code")) if value)
            probe_line = f"Provider probe: failed{f' [{identity}]' if identity else ''}: {error.get('message') or 'unknown error'}"
        else:
            probe_line = "Provider probe: not run"
        print("\n".join([
            f"GLM: {'ready' if report['ready'] else 'not ready'}", f"Provider: {report['provider']} / {report['model']}",
            f"Fallback model: {report.get('fallbackModel', FALLBACK_MODEL)}",
            f"API key: {'configured' if report['keyConfigured'] else 'missing'}", probe_line,
            f"{args.host.title()} stop gate: {'enabled' if report['reviewGateEnabled'] else 'disabled'}",
        ]))
    return 0 if report["ready"] else 1


def command_task(args: argparse.Namespace) -> int:
    cwd = workspace_root(args.cwd or os.getcwd())
    resume_id = args.resume
    if args.resume_last:
        resume_id = latest_task_session(cwd, args.host)
        if not resume_id:
            raise RuntimeError(f"No resumable GLM task found for {args.host} in this workspace.")
    prompt = read_prompt(args, allow_empty=bool(resume_id)) or "Continue the previous task."
    context = task_context(args, resumed=bool(resume_id))
    is_gate = bool(args.stop_gate)
    request = {
        "host": args.host, "kind": "stop-gate" if is_gate else "task", "jobClass": "gate" if is_gate else "task",
        "title": "GLM Stop Gate Review" if is_gate else ("GLM Resume" if resume_id else "GLM Task"),
        "summary": shorten(prompt), "cwd": str(cwd), "prompt": combine_context(context, prompt), "write": args.write,
        "resume_session_id": resume_id, "model": args.model, "effort": args.effort,
        "max_budget_usd": args.max_budget_usd, "timeout_seconds": args.timeout_seconds,
        "contextSource": context.get("sourcePath") if context else None,
        "contextMessageCount": context.get("messageCount") if context else 0,
    }
    return launch(request, args.background, args.wait, args.json)


def command_review(args: argparse.Namespace, adversarial: bool) -> int:
    cwd, target = review_target(Path(args.cwd or os.getcwd()).resolve(), args.scope, args.base)
    kind = "adversarial-review" if adversarial else "review"
    focus = " ".join(args.focus).strip() or "No additional focus."
    request = {
        "host": args.host, "kind": kind, "jobClass": "review",
        "title": "GLM Adversarial Review" if adversarial else "GLM Review", "summary": target,
        "target": target, "cwd": str(cwd), "prompt": template(f"{kind}.md", {"TARGET": target, "FOCUS": focus}),
        "write": False, "model": args.model, "effort": args.effort, "max_budget_usd": args.max_budget_usd,
        "timeout_seconds": args.timeout_seconds, "json_schema": json.loads(REVIEW_SCHEMA.read_text(encoding="utf-8")),
    }
    return launch(request, args.background, args.wait, args.json)


def command_transfer(args: argparse.Namespace) -> int:
    cwd = workspace_root(args.cwd or os.getcwd())
    context = load_context(args.host, source=args.source, session_id=args.session_id)
    session = str(uuid.uuid4())
    request = {
        "host": args.host, "kind": "transfer", "jobClass": "transfer", "title": "GLM Transfer",
        "summary": f"Transfer {context['messageCount']} visible {args.host} messages", "cwd": str(cwd),
        "prompt": context["text"] + "\n\nImport this visible conversation as working context, acknowledge briefly, and wait for the next instruction.",
        "write": False, "session_id": session, "disable_tools": True, "model": args.model, "effort": args.effort,
        "max_budget_usd": args.max_budget_usd, "timeout_seconds": args.timeout_seconds,
        "contextSource": context["sourcePath"], "contextMessageCount": context["messageCount"],
    }
    return launch(request, args.background, args.wait, args.json)


def elapsed(job: dict[str, Any]) -> str:
    try:
        start = dt.datetime.fromisoformat(job.get("startedAt") or job["createdAt"])
        end = dt.datetime.fromisoformat(job["completedAt"]) if job.get("completedAt") else dt.datetime.now(dt.timezone.utc)
        seconds = max(0, int((end - start).total_seconds()))
        return f"{seconds // 60}m {seconds % 60}s" if seconds >= 60 else f"{seconds}s"
    except (KeyError, TypeError, ValueError):
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
    jobs = [resolve_job(cwd, args.reference)] if args.reference else list_jobs(cwd, include_all=args.all)
    payload = [{**job, "elapsed": elapsed(job)} for job in jobs]
    if args.json:
        print(json.dumps(payload[0] if args.reference else payload, indent=2, ensure_ascii=False))
    elif args.reference:
        job = payload[0]
        print(f"Job: {job['id']}\nHost: {job.get('host')}\nStatus: {job.get('status')}\nPhase: {job.get('phase')}\nElapsed: {job['elapsed']}")
    else:
        print("| Job | Host | Kind | Status | Elapsed | Summary |\n|---|---|---|---|---|---|")
        for job in payload:
            print(f"| {job['id']} | {job.get('host')} | {job.get('kind')} | {job.get('status')} | {job['elapsed']} | {shorten(job.get('summary', ''), 60)} |")
    return 0


def command_result(args: argparse.Namespace) -> int:
    cwd = workspace_root(args.cwd or os.getcwd())
    job = resolve_job(cwd, args.reference, FINISHED_STATUSES)
    stored = read_job(cwd, str(job["id"]))
    print(json.dumps(stored, indent=2, ensure_ascii=False) if args.json else stored.get("rendered") or stored.get("errorMessage") or "No result.", end="\n" if args.json else "")
    return 0 if stored.get("status") == "completed" else 1


def command_cancel(args: argparse.Namespace) -> int:
    job = cancel_job(workspace_root(args.cwd or os.getcwd()), args.reference)
    print(json.dumps(job, indent=2, ensure_ascii=False) if args.json else f"Cancelled GLM job {job['id']}.")
    return 0


def command_candidate(args: argparse.Namespace) -> int:
    session = latest_task_session(workspace_root(args.cwd or os.getcwd()), args.host)
    payload = {"available": bool(session), "glmSessionId": session, "host": args.host}
    print(json.dumps(payload, indent=2) if args.json else (f"Resumable GLM session: {session}" if session else "No resumable GLM session found."))
    return 0


def command_worker(args: argparse.Namespace) -> int:
    cwd = workspace_root(args.cwd)
    job = read_job(cwd, args.job_id)
    if job.get("status") == "cancelled":
        return 0
    request = job.get("request")
    if not isinstance(request, dict):
        raise RuntimeError(f"Stored job {args.job_id} has no request.")
    result, _ = run_tracked(job, request)
    return int(result.get("status") or 0)


def host_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", choices=("codex", "claude"), required=True)


def runtime_args(parser: argparse.ArgumentParser) -> None:
    host_arg(parser)
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
    host_arg(setup); setup.add_argument("--cwd"); setup.add_argument("--enable-review-gate", action="store_true"); setup.add_argument("--disable-review-gate", action="store_true"); setup.add_argument("--no-probe", action="store_true"); setup.add_argument("--json", action="store_true"); setup.set_defaults(handler=command_setup)
    task = commands.add_parser("task", aliases=["rescue"])
    runtime_args(task); task.add_argument("--write", action="store_true")
    resumes = task.add_mutually_exclusive_group(); resumes.add_argument("--resume-last", action="store_true"); resumes.add_argument("--resume"); resumes.add_argument("--fresh", action="store_true")
    context = task.add_mutually_exclusive_group(); context.add_argument("--context-current", action="store_true"); context.add_argument("--no-context", action="store_true")
    task.add_argument("--source"); task.add_argument("--session-id"); task.add_argument("--prompt-file"); task.add_argument("--stop-gate", action="store_true", help=argparse.SUPPRESS); task.add_argument("prompt", nargs="*"); task.set_defaults(handler=command_task)
    for name, adversarial in (("review", False), ("adversarial-review", True)):
        review = commands.add_parser(name); runtime_args(review); review.add_argument("--base"); review.add_argument("--scope", choices=("auto", "working-tree", "branch"), default="auto"); review.add_argument("focus", nargs="*"); review.set_defaults(handler=lambda args, selected=adversarial: command_review(args, selected))
    transfer = commands.add_parser("transfer"); runtime_args(transfer); transfer.add_argument("--source"); transfer.add_argument("--session-id"); transfer.set_defaults(handler=command_transfer)
    status = commands.add_parser("status"); host_arg(status); status.add_argument("reference", nargs="?"); status.add_argument("--cwd"); status.add_argument("--wait", action="store_true"); status.add_argument("--timeout-ms", type=int, default=240000); status.add_argument("--poll-interval-ms", type=int, default=2000); status.add_argument("--all", action="store_true"); status.add_argument("--json", action="store_true"); status.set_defaults(handler=command_status)
    result = commands.add_parser("result"); host_arg(result); result.add_argument("reference", nargs="?"); result.add_argument("--cwd"); result.add_argument("--json", action="store_true"); result.set_defaults(handler=command_result)
    cancel = commands.add_parser("cancel"); host_arg(cancel); cancel.add_argument("reference", nargs="?"); cancel.add_argument("--cwd"); cancel.add_argument("--json", action="store_true"); cancel.set_defaults(handler=command_cancel)
    candidate = commands.add_parser("task-resume-candidate"); host_arg(candidate); candidate.add_argument("--cwd"); candidate.add_argument("--json", action="store_true"); candidate.set_defaults(handler=command_candidate)
    worker = commands.add_parser("_worker"); worker.add_argument("--cwd", required=True); worker.add_argument("--job-id", required=True); worker.set_defaults(handler=command_worker)
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
