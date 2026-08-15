from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_glm_review.py"
SPEC = importlib.util.spec_from_file_location("run_glm_review", MODULE_PATH)
assert SPEC and SPEC.loader
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


class GlmReviewAdapterTests(unittest.TestCase):
    def arguments(self, root: Path, output: Path):
        return adapter.parser().parse_args([
            "--review-type", "spec", "--cwd", str(root), "--output-file", str(output),
            "--spec-path", str(root / "spec.md"), "--timeout-seconds", "5",
        ])

    def fake_companion(self, root: Path, payload: dict) -> str:
        path = root / "glm-companion"
        path.write_text(
            "#!/usr/bin/env python3\nimport json, sys\n"
            "assert sys.argv[sys.argv.index('--timeout-seconds') + 1] == '5'\n"
            "print(json.dumps(" + repr(payload) + "))\n",
            encoding="utf-8",
        )
        path.chmod(0o755)
        return str(path)

    def test_success_writes_review_and_records_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "spec.md").write_text("# Spec\n", encoding="utf-8")
            output = root / "review.md"
            payload = {
                "rawOutput": "Verdict global: PASS\n\nNo findings.",
                "model": "glm-5.2",
                "fallbackFrom": "glm-5.3",
            }
            result = adapter.run_review(self.arguments(root, output), self.fake_companion(root, payload))
            self.assertEqual(result, 0)
            self.assertIn("Verdict global: PASS", output.read_text(encoding="utf-8"))
            self.assertIn('"fallbackFrom": "glm-5.3"', Path(f"{output}.runtime.log").read_text(encoding="utf-8"))

    def test_missing_verdict_fails_without_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "spec.md").write_text("# Spec\n", encoding="utf-8")
            output = root / "review.md"
            payload = {"rawOutput": "Analysis only", "model": "glm-4.7"}
            result = adapter.run_review(self.arguments(root, output), self.fake_companion(root, payload))
            self.assertEqual(result, 2)
            self.assertFalse(output.exists())

    def test_prompt_is_read_only_and_contains_target(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "review.md"
            args = self.arguments(root, output)
            prompt = adapter.render_prompt(args)
            self.assertIn(str(root / "spec.md"), prompt)
            self.assertIn("do not write files", prompt)

    def test_resolver_finds_marketplace_dependency_script(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp)
            script = config / "plugins" / "cache" / "cloclo" / "glm" / "1.0.0" / "scripts" / "glm_companion.py"
            script.parent.mkdir(parents=True)
            script.write_text("print('ok')\n", encoding="utf-8")
            with (
                mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(config)}, clear=True),
                mock.patch.object(adapter, "ROOT", config / "unrelated" / "cloclo"),
                mock.patch.object(adapter.shutil, "which", return_value=None),
            ):
                command = adapter.resolve_companion()
            self.assertEqual(command, [adapter.sys.executable, str(script)])


if __name__ == "__main__":
    unittest.main()
