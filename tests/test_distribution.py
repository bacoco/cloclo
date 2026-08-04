from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class DistributionContractTests(unittest.TestCase):
    def test_marketplaces_expose_the_expected_companions(self):
        claude = load_json(ROOT / ".claude-plugin" / "marketplace.json")
        codex = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
        self.assertEqual({item["name"] for item in claude["plugins"]}, {"cloclo", "glm"})
        self.assertEqual({item["name"] for item in codex["plugins"]}, {"claude", "glm"})

    def test_distribution_versions_and_dependency_are_synchronized(self):
        claude_marketplace = load_json(ROOT / ".claude-plugin" / "marketplace.json")
        published = {item["name"]: item["version"] for item in claude_marketplace["plugins"]}
        cloclo = load_json(ROOT / "plugins" / "cloclo" / ".claude-plugin" / "plugin.json")
        glm_claude = load_json(ROOT / "plugins" / "glm" / ".claude-plugin" / "plugin.json")
        glm_codex = load_json(ROOT / "plugins" / "glm" / ".codex-plugin" / "plugin.json")
        claude_codex = load_json(ROOT / "plugins" / "claude" / ".codex-plugin" / "plugin.json")
        self.assertEqual(published, {"cloclo": cloclo["version"], "glm": glm_claude["version"]})
        self.assertEqual(glm_claude["version"], glm_codex["version"])
        self.assertEqual(claude_codex["version"], "1.0.0")
        self.assertIn("glm", cloclo["dependencies"])

    def test_companion_entry_points_are_executable(self):
        for name in ("claude", "glm"):
            path = ROOT / "plugins" / name / "bin" / f"{name}-companion"
            self.assertTrue(path.is_file(), path)
            self.assertTrue(os.access(path, os.X_OK), path)

    def test_cloclo_glm_docs_use_the_dependency_bridge(self):
        command = (ROOT / "plugins" / "cloclo" / "commands" / "glm.md").read_text(encoding="utf-8")
        prerequisites = (
            ROOT / "plugins" / "cloclo" / "skills" / "pipeline" / "references" / "prerequisites.md"
        ).read_text(encoding="utf-8")
        self.assertIn("run_glm_companion.py", command)
        self.assertIn("run_glm_companion.py", prerequisites)
        self.assertNotIn("--probe", prerequisites)

    def test_no_provider_key_is_embedded_in_distribution(self):
        key_pattern = re.compile(r"\b[0-9a-fA-F]{32}\.[A-Za-z0-9_-]{16,}\b")
        offenders = []
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, text=True, stdout=subprocess.PIPE, check=True
        ).stdout.splitlines()
        for relative in tracked:
            path = ROOT / relative
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if key_pattern.search(text):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
