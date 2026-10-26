"""S01 F-01 acceptance tests: switch implicit invocation through the installed launcher.

Planner-written repair contract tests. Each test drives the real installed launcher as a
subprocess with PYTHONPATH cleared, so the command imports the installed runtime exactly
as a user's PATH command does.

Planner verification (2026-10-27, Claude Code planning session):
- On 88ff1c4 (delivery head plus review commit): A01-A05 fail with the F-01 guard error;
  A06-A07 pass. Use these as the baseline expectations when locking this file.
- A throwaway prototype (not committed) that adds a setting-only path for a current
  install, rewriting only the installed openai.yaml line and the manifest (with the skill
  fingerprint refreshed) and keeping the source-checkout guard for real upgrades, passes
  these 7 tests and all 205 existing tests.
- Locked interface found by that check: the setting-only plan's actions must include the
  exact item "set implicit invocation: <on|off>" with no suffix, because
  test_installer.test_implicit_invocation_switch_changes_plan_and_installed_policy
  matches it exactly.
- Integrity is checked in-process with installer.artifact_matches rather than through
  "doctor --json", which can trigger a quota read.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_copilot import installer
from codex_copilot.paths import repo_root


def environment(root):
    base = Path(root) / "launcher path"
    return {"CODEX_HOME": str(base / "codex"), "CODEX_COPILOT_SKILLS_HOME": str(base / "skills"),
            "CODEX_COPILOT_BIN_DIR": str(base / "bin"), "CODEX_COPILOT_SHARE_DIR": str(base / "runtime"),
            "CODEX_COPILOT_STATE_DIR": str(base / "state")}


class InstalledLauncherSettingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, environment(self.temp.name))
        self.env.start()
        self.addCleanup(self.env.stop)
        bin_dir = Path(os.environ["CODEX_COPILOT_BIN_DIR"])
        self.launcher = bin_dir / ("codex-copilot.py" if os.name == "nt" else "codex-copilot")
        self.manifest = Path(os.environ["CODEX_COPILOT_STATE_DIR"]) / "install.json"
        self.policy = Path(os.environ["CODEX_COPILOT_SKILLS_HOME"]) / "codex-copilot" / "agents" / "openai.yaml"
        self.share = Path(os.environ["CODEX_COPILOT_SHARE_DIR"])

    def install_from_source(self, value):
        installer.install(implicit_invocation=value)

    def run_launcher(self, *args):
        child = dict(os.environ)
        child.pop("PYTHONPATH", None)
        return subprocess.run([sys.executable, str(self.launcher), *args], env=child, cwd=self.temp.name,
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=60)

    def policy_value(self):
        return "true" if "  allow_implicit_invocation: true" in self.policy.read_text(encoding="utf-8") else "false"

    def assert_switch(self, initial, desired, policy):
        self.install_from_source(initial)
        distribution = installer._distribution_fingerprint(self.share)
        result = self.run_launcher("install", "--implicit-invocation", desired, "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"set implicit invocation: {desired}", result.stdout)
        self.assertEqual(json.loads(self.manifest.read_text(encoding="utf-8"))["implicit_invocation"], desired)
        self.assertEqual(self.policy_value(), policy)
        self.assertIn("  allow_implicit_invocation: false",
                      (repo_root() / "skill" / "codex-copilot" / "agents" / "openai.yaml").read_text(encoding="utf-8"))
        self.assertEqual(installer._distribution_fingerprint(self.share), distribution)
        # Same integrity rule doctor uses, checked in-process so no quota read is triggered.
        record = json.loads(self.manifest.read_text(encoding="utf-8"))
        for item in record["artifacts"]:
            self.assertTrue(installer.artifact_matches(item), item["target"])

    def test_a01_installed_launcher_turns_implicit_invocation_on(self):
        self.assert_switch("off", "on", "true")

    def test_a02_installed_launcher_turns_implicit_invocation_off(self):
        self.assert_switch("on", "off", "false")

    def test_a03_dry_run_previews_setting_only_change(self):
        self.install_from_source("off")
        before = self.manifest.read_bytes()
        result = self.run_launcher("install", "--implicit-invocation", "on", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("set implicit invocation: on", result.stdout)
        self.assertIn("Dry run: no changes made.", result.stdout)
        self.assertEqual(self.manifest.read_bytes(), before)
        self.assertEqual(self.policy_value(), "false")

    def test_a04_unconfirmed_setting_change_shows_plan_and_changes_nothing(self):
        self.install_from_source("off")
        before = self.manifest.read_bytes()
        result = self.run_launcher("install", "--implicit-invocation", "on")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("set implicit invocation: on", result.stdout)
        self.assertEqual(self.manifest.read_bytes(), before)
        self.assertEqual(self.policy_value(), "false")

    def test_a05_invalid_installed_policy_rolls_back_setting_change(self):
        self.install_from_source("off")
        self.policy.write_text(self.policy.read_text(encoding="utf-8") + "  allow_implicit_invocation: false\n", encoding="utf-8")
        record = json.loads(self.manifest.read_text(encoding="utf-8"))
        for item in record["artifacts"]:
            if item["kind"] == "skill":
                item["fingerprint"] = installer.artifact_fingerprint(Path(item["target"]))
        self.manifest.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        before_manifest, before_policy = self.manifest.read_bytes(), self.policy.read_bytes()
        result = self.run_launcher("install", "--implicit-invocation", "on", "--yes")
        self.assertEqual(result.returncode, 1)
        self.assertIn("implicit invocation line", result.stderr)
        self.assertEqual(self.manifest.read_bytes(), before_manifest)
        self.assertEqual(self.policy.read_bytes(), before_policy)

    def test_a06_same_setting_is_already_installed(self):
        self.install_from_source("on")
        before = self.manifest.read_bytes()
        result = self.run_launcher("install", "--implicit-invocation", "on", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Already installed; no changes.", result.stdout)
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_a07_upgrade_from_installed_copy_is_still_refused(self):
        self.install_from_source("off")
        record = json.loads(self.manifest.read_text(encoding="utf-8"))
        record["version"] = "0.0.0-older"
        self.manifest.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = self.run_launcher("install", "--implicit-invocation", "on", "--yes")
        self.assertEqual(result.returncode, 1)
        self.assertIn("source checkout outside the installed copy", result.stderr)
        self.assertEqual(json.loads(self.manifest.read_text(encoding="utf-8"))["implicit_invocation"], "off")


if __name__ == "__main__":
    unittest.main()
