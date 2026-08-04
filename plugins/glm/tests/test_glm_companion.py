#!/usr/bin/env python3
"""Regression tests for the shared Codex/Claude GLM companion."""

# PDG-LARGE-FILE-JUSTIFICATION: One contract suite keeps cross-host context,
# provider fallback, permissions, resume, and stop-gate parity visible together.

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

import glm_companion  # noqa: E402
import glm_runtime  # noqa: E402
import glm_state  # noqa: E402
import host_context  # noqa: E402
import stop_review_gate  # noqa: E402


class ContextContracts(unittest.TestCase):
    def write_jsonl(self, rows: list[dict]) -> Path:
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        with handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")
        return Path(handle.name)

    def test_codex_export_keeps_only_visible_messages(self) -> None:
        source = self.write_jsonl([
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]}},
            {"type": "response_item", "payload": {"type": "reasoning", "summary": "hidden"}},
            {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "world"}]}},
        ])
        self.assertEqual(host_context.codex_messages(source), [{"role": "user", "text": "hello"}, {"role": "assistant", "text": "world"}])

    def test_claude_export_excludes_tools_meta_and_sidechains(self) -> None:
        source = self.write_jsonl([
            {"type": "user", "message": {"role": "user", "content": "visible"}},
            {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "thinking", "thinking": "hidden"}, {"type": "text", "text": "answer"}]}},
            {"type": "user", "isMeta": True, "message": {"role": "user", "content": "meta"}},
            {"type": "assistant", "isSidechain": True, "message": {"role": "assistant", "content": "agent"}},
        ])
        self.assertEqual(host_context.claude_messages(source), [{"role": "user", "text": "visible"}, {"role": "assistant", "text": "answer"}])

    def test_context_redacts_provider_keys(self) -> None:
        secret = "a" * 32 + "." + "B" * 20
        source = self.write_jsonl([
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": f"use {secret}"}]}},
        ])
        messages = host_context.codex_messages(source)
        self.assertNotIn(secret, messages[0]["text"])
        self.assertIn("[REDACTED_SECRET]", messages[0]["text"])

    def test_single_large_context_message_is_strictly_bounded(self) -> None:
        selected = host_context.bounded_messages([{"role": "user", "text": "x" * 130_000}])
        self.assertLessEqual(len(selected[0]["text"]) + 32, host_context.MAX_CONTEXT_CHARS)
        self.assertIn("truncated", selected[0]["text"])


class RuntimeContracts(unittest.TestCase):
    def test_command_pins_glm_52(self) -> None:
        with (
            mock.patch.object(glm_runtime, "find_claude", return_value="claude"),
            mock.patch.object(glm_runtime, "sandbox_command", side_effect=lambda command, request, write: command),
        ):
            command = glm_runtime.build_command({"cwd": "/tmp", "write": False})
        self.assertEqual(command[command.index("--model") + 1], "glm-5.2")

    def test_write_mode_is_explicitly_forwarded_to_transport(self) -> None:
        with (
            mock.patch.object(glm_runtime, "find_claude", return_value="claude"),
            mock.patch.object(glm_runtime, "sandbox_command", side_effect=lambda command, request, write: command),
        ):
            command = glm_runtime.build_command({"cwd": "/tmp", "write": True})
        self.assertEqual(command[command.index("--permission-mode") + 1], "acceptEdits")
        self.assertNotIn("--disallowedTools", command)

    def test_provider_environment_is_child_scoped(self) -> None:
        with (
            mock.patch.object(glm_runtime, "_env_value", return_value=None),
            mock.patch.dict(os.environ, {"ZAI_API_KEY": "secret", "ANTHROPIC_API_KEY": "wrong"}, clear=True),
        ):
            child = glm_runtime.provider_env("/tmp", "glm-5.2")
            self.assertNotIn("ANTHROPIC_API_KEY", child)
            self.assertEqual(child["ANTHROPIC_AUTH_TOKEN"], "secret")
            self.assertEqual(child["ANTHROPIC_DEFAULT_HAIKU_MODEL"], "glm-4.7")
            self.assertEqual(child["ANTHROPIC_DEFAULT_SONNET_MODEL"], "glm-5.2")
            self.assertNotIn("CLAUDE_CODE_AUTO_COMPACT_WINDOW", child)
            self.assertEqual(child["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"], "1")
            self.assertEqual(child["API_TIMEOUT_MS"], "3000000")
            self.assertEqual(os.environ["ANTHROPIC_API_KEY"], "wrong")

    def test_personal_secret_file_precedes_stale_environment(self) -> None:
        with (
            mock.patch.object(glm_runtime, "_env_value", return_value="new-secret"),
            mock.patch.dict(os.environ, {"ZAI_API_KEY": "old-secret"}, clear=True),
        ):
            key, source = glm_runtime.resolve_key("/tmp")
        self.assertEqual(key, "new-secret")
        self.assertEqual(source, f"file:{Path.home() / '.glm.env'}")

    def test_provider_probe_lists_models_without_inference(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "object": "list", "data": [{"id": "glm-5.2"}],
        }).encode()
        with (
            mock.patch.object(glm_runtime, "resolve_key", return_value=("secret", "test")),
            mock.patch.object(glm_runtime.urllib.request, "urlopen", return_value=response) as urlopen,
        ):
            result = glm_runtime.probe_provider("/tmp", "glm-5.2[1m]")
        self.assertTrue(result["reachable"])
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, glm_runtime.ZAI_MODELS_URL)
        self.assertEqual(request.method, "GET")
        self.assertIsNone(request.data)

    def test_rate_limited_glm_52_falls_back_to_glm_47(self) -> None:
        failed = {"status": 1, "model": "glm-5.2", "providerRetryCount": 3, "errorMessage": "rate_limit"}
        passed = {"status": 0, "model": "glm-4.7", "providerRetryCount": 0, "rawOutput": "ok"}
        with mock.patch.object(glm_runtime, "_run_glm_once", side_effect=[failed, passed]) as run_once:
            result = glm_runtime.run_glm({"cwd": "/tmp", "prompt": "test"})
        self.assertEqual(run_once.call_count, 2)
        self.assertEqual(run_once.call_args_list[0].args[0]["model"], "glm-5.2")
        self.assertEqual(run_once.call_args_list[1].args[0]["model"], "glm-4.7")
        self.assertEqual(result["fallbackFrom"], "glm-5.2")
        self.assertEqual(result["rawOutput"], "ok")

    def test_non_rate_provider_failure_does_not_change_models(self) -> None:
        failed = {"status": 1, "model": "glm-5.2", "providerRetryCount": 3, "errorMessage": "network timeout"}
        with mock.patch.object(glm_runtime, "_run_glm_once", return_value=failed) as run_once:
            result = glm_runtime.run_glm({"cwd": "/tmp", "prompt": "test"})
        self.assertEqual(run_once.call_count, 1)
        self.assertNotIn("fallbackFrom", result)

    def test_documented_state_root_override_is_supported(self) -> None:
        with mock.patch.dict(os.environ, {"GLM_COMPANION_HOME": "/tmp/glm-home"}, clear=True):
            self.assertEqual(glm_state.state_root(), Path("/tmp/glm-home").resolve() / "state")

    def test_recursion_is_blocked_before_spawn(self) -> None:
        with mock.patch.dict(os.environ, {glm_runtime.DEPTH_ENV: "1"}):
            with self.assertRaisesRegex(RuntimeError, "Recursive"):
                glm_runtime.run_glm({"cwd": ".", "prompt": "test"})

    def test_automatic_missing_context_degrades_cleanly(self) -> None:
        args = argparse.Namespace(host="codex", context_current=False, source=None, session_id=None, no_context=False)
        with mock.patch.object(glm_companion, "load_context", side_effect=RuntimeError("missing")):
            self.assertIsNone(glm_companion.task_context(args, resumed=False))

    def test_transfer_failure_has_no_resume_command(self) -> None:
        request = {"host": "codex", "kind": "transfer", "title": "GLM Transfer", "contextMessageCount": 2, "contextSource": None}
        failed = {"status": 1, "sessionId": None, "rawOutput": "", "errorMessage": "failed"}
        with mock.patch.object(glm_companion, "run_glm", return_value=failed):
            result, rendered = glm_companion.execute_request(request)
        self.assertIsNone(result["resumeCommand"])
        self.assertNotIn("resume None", rendered)

    def test_transfer_resume_stays_inside_glm_companion(self) -> None:
        request = {"host": "claude", "kind": "transfer", "title": "GLM Transfer", "contextMessageCount": 2, "contextSource": None}
        passed = {"status": 0, "sessionId": "glm-session", "rawOutput": "ready", "errorMessage": ""}
        with mock.patch.object(glm_companion, "run_glm", return_value=passed):
            result, rendered = glm_companion.execute_request(request)
        expected = f"{glm_companion.ROOT / 'bin' / 'glm-companion'} task --host claude --resume glm-session"
        self.assertEqual(result["resumeCommand"], expected)
        self.assertIn(expected, rendered)
        self.assertNotIn("with `claude --resume", rendered)

    def test_resume_candidates_are_host_isolated(self) -> None:
        jobs = [
            {"host": "claude", "kind": "task", "jobClass": "task", "status": "completed", "glmSessionId": "c"},
            {"host": "codex", "kind": "task", "jobClass": "task", "status": "completed", "glmSessionId": "x"},
        ]
        with mock.patch.object(glm_state, "list_jobs", return_value=jobs):
            self.assertEqual(glm_state.latest_task_session(".", "codex"), "x")

    def test_background_enqueue_records_worker_pid(self) -> None:
        process = mock.MagicMock(pid=4242)
        job = {"id": "task-test", "logFile": None}
        with (
            mock.patch.object(glm_companion.subprocess, "Popen", return_value=process),
            mock.patch.object(glm_companion, "update_job") as update,
            mock.patch.object(glm_companion, "read_job", return_value={"id": "task-test", "pid": 4242}),
        ):
            result = glm_companion.enqueue(Path("/tmp"), job)
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
            with mock.patch.object(glm_state, "state_dir", return_value=root):
                glm_state.save_state("/tmp", {"config": {}, "jobs": jobs})
            self.assertFalse((directory / "job-00.json").exists())
            self.assertFalse((directory / "job-00.log").exists())
            self.assertTrue((directory / "job-50.json").exists())
            self.assertEqual(len(json.loads((root / "state.json").read_text())["jobs"]), 50)

    def test_setup_text_exposes_provider_error_code(self) -> None:
        args = argparse.Namespace(host="codex", cwd="/tmp", enable_review_gate=False, disable_review_gate=False, no_probe=False, json=False)
        report = {
            "ready": False, "provider": "Z.ai", "model": "glm-5.2", "keyConfigured": True,
            "providerProbe": {"reachable": False, "error": {"type": "api_error", "code": "1313", "message": "limited"}},
        }
        with (
            mock.patch.object(glm_companion, "workspace_root", return_value=Path("/tmp")),
            mock.patch.object(glm_companion, "setup_report", return_value=report),
            mock.patch.object(glm_companion, "get_config", return_value={}),
            mock.patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            self.assertEqual(glm_companion.command_setup(args), 1)
            self.assertIn("[api_error/1313]", stdout.getvalue())


class StopGateContracts(unittest.TestCase):
    def run_gate(self, completed: subprocess.CompletedProcess[str]) -> tuple[str, str]:
        with (
            mock.patch.object(stop_review_gate, "input_data", return_value={"cwd": "/tmp"}),
            mock.patch.object(stop_review_gate, "workspace_root", return_value=Path("/tmp")),
            mock.patch.object(stop_review_gate, "list_jobs", return_value=[]),
            mock.patch.object(stop_review_gate, "get_config", return_value={"stopReviewGateCodex": True}),
            mock.patch.object(stop_review_gate, "setup_report", return_value={"ready": True}),
            mock.patch.object(stop_review_gate.subprocess, "run", return_value=completed),
            mock.patch("sys.stdout", new_callable=io.StringIO) as stdout,
            mock.patch("sys.stderr", new_callable=io.StringIO) as stderr,
        ):
            self.assertEqual(stop_review_gate.main(), 0)
            return stdout.getvalue(), stderr.getvalue()

    def test_provider_failure_fails_open(self) -> None:
        stdout, stderr = self.run_gate(subprocess.CompletedProcess([], 1, "", "rate limited"))
        self.assertEqual(stdout, "")
        self.assertIn("allowing stop", stderr)

    def test_only_explicit_block_blocks(self) -> None:
        payload = json.dumps({"rawOutput": "BLOCK: concrete defect"})
        stdout, _ = self.run_gate(subprocess.CompletedProcess([], 0, payload, ""))
        self.assertEqual(json.loads(stdout)["decision"], "block")


if __name__ == "__main__":
    unittest.main()
