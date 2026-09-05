import os
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_copilot.installer import InstallError, install, load_manifest, uninstall


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

    def test_symlink_install_is_idempotent_and_uninstalls(self):
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
                self.assertEqual(parsed["model"], "gpt-5.6-terra")
                self.assertTrue(parsed["features"]["multi_agent"])
                self.assertEqual(parsed["agents"]["default_subagent_model"], "gpt-5.6-luna")
                self.assertTrue((Path(env["CODEX_COPILOT_SKILLS_HOME"]) / "codex-copilot").is_symlink())
                result = uninstall()
                self.assertTrue(result["changed"])
                restored = tomllib.loads(config.read_text())
                self.assertEqual(restored["model"], "gpt-5.6-sol")
                self.assertTrue(restored["mcp_servers"]["demo"]["enabled"])

    def test_copy_mode_and_dry_run(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            with patch.dict(os.environ, env, clear=False):
                result = install(mode="copy", dry_run=True)
                self.assertTrue(result["dry_run"])
                self.assertFalse(Path(env["CODEX_COPILOT_STATE_DIR"]).exists())
                install(mode="copy")
                skill = Path(env["CODEX_COPILOT_SKILLS_HOME"]) / "codex-copilot"
                self.assertTrue(skill.is_dir())
                self.assertFalse(skill.is_symlink())
                uninstall()
                self.assertFalse(skill.exists())

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
                install()
                config = Path(env["CODEX_HOME"]) / "config.toml"
                config.write_text(config.read_text().replace('model = "gpt-5.6-terra"', 'model = "custom"'))
                result = uninstall()
                self.assertTrue(any("model" in warning for warning in result["warnings"]))
                self.assertEqual(tomllib.loads(config.read_text())["model"], "custom")


if __name__ == "__main__":
    unittest.main()
