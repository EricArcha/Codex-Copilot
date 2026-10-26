"""Installer-owned regressions for the F-01 setting-only eligibility boundary."""

import json
import os
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_copilot import installer
from tests.test_installed_launcher import environment


class SettingOnlyInstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.env = environment(temporary.name)
        override = patch.dict(os.environ, self.env)
        override.start()
        self.addCleanup(override.stop)
        self.config = Path(self.env["CODEX_HOME"]) / "config.toml"
        self.config.parent.mkdir(parents=True)
        self.original_config = '# user settings\nmodel = "custom-model"\n'
        self.config.write_text(self.original_config, encoding="utf-8")
        installer.install()
        self.share = Path(self.env["CODEX_COPILOT_SHARE_DIR"])
        self.policy = Path(self.env["CODEX_COPILOT_SKILLS_HOME"]) / "codex-copilot" / "agents" / "openai.yaml"
        installed_root = patch.object(installer, "repo_root", return_value=self.share)
        installed_root.start()
        self.addCleanup(installed_root.stop)

    def write_manifest(self, record):
        installer.manifest_path().write_text(json.dumps(record), encoding="utf-8")

    def test_only_policy_and_manifest_change_and_uninstall_retains_original_ownership(self):
        before = installer.load_manifest()
        config = self.config.read_bytes()
        other = {item["target"]: installer.artifact_fingerprint_for(item)
                 for item in before["artifacts"] if item["kind"] != "skill"}
        preview = installer.install(dry_run=True, implicit_invocation="on")
        self.assertEqual(preview["actions"], ["set implicit invocation: on"])
        result = installer.install(implicit_invocation="on", expected_plan_token=preview["plan_token"])
        self.assertTrue(result["changed"])
        after = installer.load_manifest()
        for key in before.keys() - {"implicit_invocation", "artifacts"}:
            self.assertEqual(after[key], before[key], key)
        for item in after["artifacts"]:
            self.assertTrue(installer.artifact_matches(item))
            if item["kind"] != "skill":
                self.assertEqual(installer.artifact_fingerprint_for(item), other[item["target"]])
        self.assertEqual(self.config.read_bytes(), config)
        installer.install(implicit_invocation="off")
        installer.uninstall()
        restored = self.config.read_text(encoding="utf-8")
        self.assertTrue(restored.startswith(self.original_config))
        parsed = tomllib.loads(restored)
        self.assertEqual(parsed["model"], "custom-model")
        self.assertEqual(parsed.get("features", {}), {})
        self.assertEqual(parsed.get("agents", {}), {})

    def test_changed_setting_invalidates_preview_token(self):
        preview = installer.install(dry_run=True, implicit_invocation="on")
        before = installer.manifest_path().read_bytes()
        with self.assertRaisesRegex(installer.InstallError, "plan changed"):
            installer.install(implicit_invocation="off", expected_plan_token=preview["plan_token"])
        self.assertEqual(installer.manifest_path().read_bytes(), before)

    def test_changed_config_invalidates_preview_without_overwriting_user_edit(self):
        preview = installer.install(dry_run=True, implicit_invocation="on")
        self.config.write_text(self.config.read_text(encoding="utf-8") + "# edited after preview\n", encoding="utf-8")
        edited = self.config.read_bytes()
        before = installer.manifest_path().read_bytes(), self.policy.read_bytes()
        with self.assertRaisesRegex(installer.InstallError, "plan changed"):
            installer.install(implicit_invocation="on", expected_plan_token=preview["plan_token"])
        self.assertEqual(self.config.read_bytes(), edited)
        self.assertEqual((installer.manifest_path().read_bytes(), self.policy.read_bytes()), before)

    def test_modified_skill_is_preserved_and_refused(self):
        self.policy.write_text(self.policy.read_text(encoding="utf-8") + "# user edit\n", encoding="utf-8")
        before = installer.manifest_path().read_bytes(), self.policy.read_bytes()
        with self.assertRaises(installer.InstallError):
            installer.install(implicit_invocation="on")
        self.assertEqual((installer.manifest_path().read_bytes(), self.policy.read_bytes()), before)

    def test_incomplete_config_cannot_use_setting_only_path(self):
        text = self.config.read_text(encoding="utf-8")
        self.assertIn("fast_mode = false", text)
        self.config.write_text(text.replace("fast_mode = false", "fast_mode = true"), encoding="utf-8")
        before = installer.manifest_path().read_bytes(), self.policy.read_bytes(), self.config.read_bytes()
        with self.assertRaisesRegex(installer.InstallError, "source checkout outside the installed copy"):
            installer.install(implicit_invocation="on")
        self.assertEqual((installer.manifest_path().read_bytes(), self.policy.read_bytes(), self.config.read_bytes()), before)

    def test_legacy_manifest_requires_real_upgrade(self):
        record = installer.load_manifest()
        record.pop("implicit_invocation")
        self.write_manifest(record)
        before = installer.manifest_path().read_bytes(), self.policy.read_bytes()
        with self.assertRaisesRegex(installer.InstallError, "source checkout outside the installed copy"):
            installer.install(implicit_invocation="on")
        self.assertEqual((installer.manifest_path().read_bytes(), self.policy.read_bytes()), before)


if __name__ == "__main__":
    unittest.main()
