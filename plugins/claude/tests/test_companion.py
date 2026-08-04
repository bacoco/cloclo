#!/usr/bin/env python3
"""Regression tests for Claude Companion's safety and lifecycle contracts."""

from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import claude_companion  # noqa: E402
import claude_runtime  # noqa: E402
import claude_state  # noqa: E402
import codex_context  # noqa: E402
import stop_review_gate  # noqa: E402


class CompanionContracts(unittest.TestCase):
    def test_visible_context_redacts_provider_keys(self) -> None:
        secret = "a" * 32 + "." + "B" * 20
        payload = {"content": [{"type": "input_text", "text": f"use {secret}"}]}
        rendered = codex_context._message_text(payload)
        self.assertNotIn(secret, rendered)
        self.assertIn("[REDACTED_SECRET]", rendered)

    def test_visible_context_is_bounded_to_recent_messages(self) -> None:
        messages = [{"role": "user", "text": str(index)} for index in range(100)]
        selected = codex_context.bounded_messages(messages)
        self.assertEqual(len(selected), 80)
        self.assertEqual(selected[0]["text"], "20")

    def test_single_large_context_message_is_strictly_bounded(self) -> None:
        selected = codex_context.bounded_messages([{"role": "user", "text": "x" * 130_000}])
        self.assertLessEqual(len(selected[0]["text"]) + 32, codex_context.MAX_CONTEXT_CHARS)
        self.assertIn("truncated", selected[0]["text"])

    def test_automatic_context_degrades_when_thread_is_unavailable(self) -> None:
        args = argparse.Namespace(
            context_current=False, source=None, thread_id=None, no_context=False
        )
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(claude_companion.context_for_task(args, is_resume=False))

    def test_explicit_thread_context_failure_is_reported(self) -> None:
        args = argparse.Namespace(
            context_current=False, source=None, thread_id="missing-thread", no_context=False
        )
        with self.assertRaises(RuntimeError):
            claude_companion.context_for_task(args, is_resume=False)

    def test_transfer_failure_never_advertises_a_resume_command(self) -> None:
        failed = {"status": 1, "sessionId": None, "errorMessage": "failed", "rawOutput": ""}
        request = {
            "kind": "transfer", "title": "Claude Transfer", "contextMessageCount": 3,
            "contextSource": None,
        }
        with mock.patch.object(claude_companion, "run_claude", return_value=failed):
            result, rendered = claude_companion.execute_request(request)
        self.assertIsNone(result["resumeCommand"])
        self.assertNotIn("claude --resume None", rendered)

    def test_resume_last_excludes_gate_sessions(self) -> None:
        jobs = [
            {"kind": "stop-gate", "jobClass": "gate", "status": "completed", "claudeSessionId": "gate"},
            {"kind": "task", "jobClass": "task", "status": "completed", "claudeSessionId": "task"},
        ]
        with mock.patch.object(claude_state, "list_jobs", return_value=jobs):
            self.assertEqual(claude_state.latest_task_session("."), "task")

    def test_read_only_sandbox_protects_workspace_and_plugin_state(self) -> None:
        if not claude_runtime.shutil.which("sandbox-exec"):
            self.skipTest("macOS sandbox-exec is unavailable")
        command = claude_runtime.sandbox_command(["claude"], {"cwd": "/tmp/workspace"}, False)
        profile = command[2]
        self.assertIn(f'(deny file-write* (subpath "{Path("/tmp/workspace").resolve()}"))', profile)
        self.assertIn(str(claude_state.state_root()), profile)

    def test_write_mode_is_explicitly_forwarded_to_claude(self) -> None:
        with mock.patch.object(claude_runtime, "find_claude", return_value="claude"):
            command = claude_runtime.build_command({"cwd": "/tmp", "write": True})
        self.assertEqual(command[command.index("--permission-mode") + 1], "acceptEdits")
        self.assertNotIn("--disallowedTools", command)

    def test_background_enqueue_records_worker_pid(self) -> None:
        process = mock.MagicMock(pid=4242)
        job = {"id": "task-test", "logFile": None}
        with (
            mock.patch.object(claude_companion.subprocess, "Popen", return_value=process),
            mock.patch.object(claude_companion, "update_job") as update,
            mock.patch.object(claude_companion, "read_job", return_value={"id": "task-test", "pid": 4242}),
        ):
            result = claude_companion.enqueue(Path("/tmp"), job)
        update.assert_called_once_with(Path("/tmp"), "task-test", {"pid": 4242})
        self.assertEqual(result["pid"], 4242)

    def test_state_pruning_removes_evicted_job_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory = root / "jobs"
            directory.mkdir()
            jobs = [
                {"id": f"job-{index:02d}", "status": "completed", "updatedAt": f"{index:02d}"}
                for index in range(51)
            ]
            for suffix in (".json", ".log"):
                (directory / f"job-00{suffix}").write_text("old", encoding="utf-8")
                (directory / f"job-50{suffix}").write_text("new", encoding="utf-8")
            with mock.patch.object(claude_state, "state_dir", return_value=root):
                claude_state.save_state("/tmp", {"config": {}, "jobs": jobs})
            self.assertFalse((directory / "job-00.json").exists())
            self.assertFalse((directory / "job-00.log").exists())
            self.assertTrue((directory / "job-50.json").exists())
            self.assertEqual(len(json.loads((root / "state.json").read_text())["jobs"]), 50)

    def test_delegation_depth_blocks_recursion_before_spawn(self) -> None:
        with mock.patch.dict(os.environ, {claude_runtime.DELEGATION_DEPTH_ENV: "1"}):
            with self.assertRaisesRegex(RuntimeError, "Recursive"):
                claude_runtime.run_claude({"cwd": ".", "prompt": "test"})


class StopGateContracts(unittest.TestCase):
    def run_gate(self, completed: subprocess.CompletedProcess[str]) -> tuple[str, str]:
        with (
            mock.patch.object(stop_review_gate, "hook_input", return_value={"cwd": "/tmp"}),
            mock.patch.object(stop_review_gate, "workspace_root", return_value=Path("/tmp")),
            mock.patch.object(stop_review_gate, "list_jobs", return_value=[]),
            mock.patch.object(stop_review_gate, "get_config", return_value={"stopReviewGate": True}),
            mock.patch.object(stop_review_gate, "setup_report", return_value={"ready": True}),
            mock.patch.object(stop_review_gate.subprocess, "run", return_value=completed),
            mock.patch("sys.stdout", new_callable=io.StringIO) as stdout,
            mock.patch("sys.stderr", new_callable=io.StringIO) as stderr,
        ):
            self.assertEqual(stop_review_gate.main(), 0)
            return stdout.getvalue(), stderr.getvalue()

    def test_infrastructure_failure_fails_open(self) -> None:
        stdout, stderr = self.run_gate(subprocess.CompletedProcess([], 1, "", "offline"))
        self.assertEqual(stdout, "")
        self.assertIn("allowing stop", stderr)

    def test_explicit_block_is_the_only_blocking_output(self) -> None:
        payload = json.dumps({"rawOutput": "BLOCK: unresolved critical defect"})
        stdout, _ = self.run_gate(subprocess.CompletedProcess([], 0, payload, ""))
        self.assertEqual(json.loads(stdout)["decision"], "block")


if __name__ == "__main__":
    unittest.main()
