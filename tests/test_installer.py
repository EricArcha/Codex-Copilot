import os
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_copilot.installer import (
    AGENT_FILES,
    MEASUREMENT_NOTICE,
    RESTART_NOTICE,
    SYMLINK_RISK_WARNING,
    InstallError,
    _is_current_install,
    artifact_matches,
    install,
    load_manifest,
    uninstall,
)


class InstallerTests(unittest.TestCase):
    def environment(self, root: str) -> dict[str, str]:
        base = Path(root)
        return {
            "CODEX_HOME": str(base / ".codex"),
            "CODEX_COPILOT_SKILLS_HOME": str(base / ".agents" / "skills"),
            "CODEX_COPILOT_BIN_DIR": str(base / ".local" / "bin"),
            "CODEX_COPILOT_SHARE_DIR": str(base / ".local" / "share" / "codex-copilot"),
            "CODEX_COPILOT_STATE_DIR": str(base / ".codex-copilot"),
        }

    def test_default_copy_install_is_idempotent_and_uninstalls(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            config = Path(env["CODEX_HOME"]) / "config.toml"
            config.parent.mkdir(parents=True)
            original = '# user comment\nmodel = "gpt-5.6-sol"\n\n[mcp_servers.demo]\nenabled = true\n'
            config.write_text(original)
            with patch.dict(os.environ, env, clear=False):
                first = install()
                second = install()
                self.assertTrue(first["changed"])
                self.assertFalse(second["changed"])
                parsed = tomllib.loads(config.read_text())
                self.assertEqual(parsed["model"], "gpt-5.6-sol")
                self.assertTrue(parsed["features"]["multi_agent"])
                self.assertEqual(parsed["agents"]["default_subagent_model"], "gpt-6-luna")
                skill = Path(env["CODEX_COPILOT_SKILLS_HOME"]) / "codex-copilot"
                self.assertTrue(skill.is_dir())
                self.assertFalse(skill.is_symlink())
                self.assertIn(RESTART_NOTICE, first["warnings"])
                self.assertIn(MEASUREMENT_NOTICE, first["warnings"])
                self.assertIn(MEASUREMENT_NOTICE, second["warnings"])
                result = uninstall()
                self.assertTrue(result["changed"])
                self.assertFalse(Path(env["CODEX_COPILOT_SHARE_DIR"]).exists())
                restored = tomllib.loads(config.read_text())
                self.assertEqual(restored["model"], "gpt-5.6-sol")
                self.assertTrue(restored["mcp_servers"]["demo"]["enabled"])

    def test_copy_mode_and_dry_run(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            with patch.dict(os.environ, env, clear=False):
                result = install(mode="copy", dry_run=True)
                self.assertTrue(result["dry_run"])
                self.assertIn(RESTART_NOTICE, result["warnings"])
                self.assertIn(MEASUREMENT_NOTICE, result["warnings"])
                self.assertNotIn(SYMLINK_RISK_WARNING, result["warnings"])
                self.assertFalse(Path(env["CODEX_COPILOT_STATE_DIR"]).exists())
                install(mode="copy")
                skill = Path(env["CODEX_COPILOT_SKILLS_HOME"]) / "codex-copilot"
                self.assertTrue(skill.is_dir())
                self.assertFalse(skill.is_symlink())
                manifest = load_manifest()
                assert manifest is not None
                distribution = next(item for item in manifest["artifacts"] if item["kind"] == "distribution")
                self.assertTrue(artifact_matches(distribution))
                (skill / ".DS_Store").write_text("macOS metadata")
                skill_artifact = next(item for item in manifest["artifacts"] if item["kind"] == "skill")
                self.assertTrue(artifact_matches(skill_artifact))
                (Path(distribution["target"]) / "VERSION").write_text("modified")
                self.assertFalse(artifact_matches(distribution))
                uninstall()
                self.assertFalse(skill.exists())

    def test_install_rejects_an_obsolete_confirmed_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            config = Path(env["CODEX_HOME"]) / "config.toml"
            config.parent.mkdir(parents=True)
            with patch.dict(os.environ, env, clear=False):
                preview = install(dry_run=True)
                config.write_text('model = "changed-after-preview"\n')
                with self.assertRaises(InstallError):
                    install(expected_plan_token=preview["plan_token"])
                self.assertFalse(Path(env["CODEX_COPILOT_STATE_DIR"]).exists())

    def test_symlink_mode_warns_and_can_be_replaced_by_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            with patch.dict(os.environ, env, clear=False):
                preview = install(mode="symlink", dry_run=True)
                self.assertIn(SYMLINK_RISK_WARNING, preview["warnings"])
                install(mode="symlink")
                skill = Path(env["CODEX_COPILOT_SKILLS_HOME"]) / "codex-copilot"
                self.assertTrue(skill.is_symlink())
                migration = install(mode="copy")
                self.assertTrue(migration["changed"])
                self.assertFalse(skill.is_symlink())
                install(mode="symlink")
                self.assertTrue(skill.is_symlink())
                self.assertFalse(Path(env["CODEX_COPILOT_SHARE_DIR"]).exists())
                self.assertTrue(uninstall()["changed"])

    def test_refuses_unknown_collision(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            target = Path(env["CODEX_COPILOT_BIN_DIR"]) / "codex-copilot"
            target.parent.mkdir(parents=True)
            target.write_text("unknown")
            with patch.dict(os.environ, env, clear=False):
                with self.assertRaises(InstallError):
                    install()

    def test_uninstall_preserves_user_changed_managed_value(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            with patch.dict(os.environ, env, clear=False):
                install(mode="symlink")
                config = Path(env["CODEX_HOME"]) / "config.toml"
                config.write_text('model = "custom"\n' + config.read_text())
                result = uninstall()
                self.assertEqual(tomllib.loads(config.read_text())["model"], "custom")

    def test_uninstall_restores_config_after_the_installed_skill_was_deleted(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            config = Path(env["CODEX_HOME"]) / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text('model = "gpt-5.6-sol"\n')
            with patch.dict(os.environ, env, clear=False):
                install()
                skill = Path(env["CODEX_COPILOT_SKILLS_HOME"]) / "codex-copilot"
                shutil.rmtree(skill)
                result = uninstall()
                self.assertTrue(result["changed"])
                restored = tomllib.loads(config.read_text())
                self.assertEqual(restored["model"], "gpt-5.6-sol")
                self.assertEqual(restored.get("features"), {})
                self.assertEqual(restored.get("agents"), {})

    def test_old_manifest_is_not_current_when_a_new_agent_is_required(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            with patch.dict(os.environ, env, clear=False):
                install()
                manifest = load_manifest()
                self.assertIsNotNone(manifest)
                assert manifest is not None
                final_target = str(Path(env["CODEX_HOME"]) / "agents" / "copilot-final-reviewer.toml")
                manifest["artifacts"] = [
                    item for item in manifest["artifacts"] if item["target"] != final_target
                ]
                config = tomllib.loads((Path(env["CODEX_HOME"]) / "config.toml").read_text())
                self.assertIn("copilot-final-reviewer.toml", AGENT_FILES)
                self.assertFalse(_is_current_install(manifest, "copy", config))


if __name__ == "__main__":
    unittest.main()
