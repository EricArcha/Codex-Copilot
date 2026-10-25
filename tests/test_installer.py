import json
import os
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch
from tests.platform_support import require_symlinks

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

    def test_repository_root_non_product_files_are_not_installed(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, self.environment(temp)):
            install()
            runtime = Path(os.environ["CODEX_COPILOT_SHARE_DIR"])
            self.assertEqual({item.name for item in runtime.iterdir()},
                             {"src", "skill", "agents", "bin", "VERSION"})
            skill = Path(os.environ["CODEX_COPILOT_SKILLS_HOME"]) / "codex-copilot"
            for name in ("docs", "scripts", "tests", "videos", "AGENTS.md", "CONTRIBUTING.md", "CHANGELOG.md"):
                self.assertFalse((runtime / name).exists())
                self.assertFalse((skill / name).exists())
            self.assertFalse(install()["changed"])

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
            require_symlinks(self, temp)
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
                install(mode="copy")
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

    def policy(self):
        return (Path(os.environ["CODEX_COPILOT_SKILLS_HOME"]) /
                "codex-copilot/agents/openai.yaml")

    def test_implicit_invocation_fresh_copy_defaults_off(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, self.environment(temp)):
            install()
            self.assertIn("  allow_implicit_invocation: false", self.policy().read_text(encoding="utf-8"))
            self.assertEqual(load_manifest()["implicit_invocation"], "off")

    def test_implicit_invocation_on_only_changes_installed_skill(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, self.environment(temp)):
            source = Path(__file__).resolve().parents[1] / "skill/codex-copilot/agents/openai.yaml"
            original = source.read_bytes()
            install(implicit_invocation="on")
            self.assertIn("  allow_implicit_invocation: true", self.policy().read_text(encoding="utf-8"))
            self.assertEqual(source.read_bytes(), original)
            copied_source = Path(os.environ["CODEX_COPILOT_SHARE_DIR"]) / "skill/codex-copilot/agents/openai.yaml"
            self.assertEqual(copied_source.read_bytes(), original)
            manifest = load_manifest()
            self.assertEqual(manifest["implicit_invocation"], "on")
            self.assertTrue(all(artifact_matches(a) for a in manifest["artifacts"]))
            uninstall()
            self.assertFalse(self.policy().exists())

    def test_implicit_invocation_upgrade_preserves_on(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, self.environment(temp)):
            install(implicit_invocation="on")
            self.assertFalse(install()["changed"])
            manifest_file = Path(os.environ["CODEX_COPILOT_STATE_DIR"]) / "install.json"
            manifest = load_manifest()
            manifest["version"] = "1.0.0"
            manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertTrue(install()["changed"])
            self.assertEqual(load_manifest()["implicit_invocation"], "on")
            self.assertIn("  allow_implicit_invocation: true", self.policy().read_text(encoding="utf-8"))

    def test_implicit_invocation_switch_changes_plan_and_installed_policy(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, self.environment(temp)):
            install()
            off = install(dry_run=True)
            on = install(dry_run=True, implicit_invocation="on")
            self.assertTrue(on["needs_confirmation"])
            self.assertIn("set implicit invocation: on", on["actions"])
            self.assertNotEqual(off["plan_token"], on["plan_token"])
            with self.assertRaisesRegex(InstallError, "plan changed"):
                install(implicit_invocation="on", expected_plan_token=off["plan_token"])
            install(implicit_invocation="on", expected_plan_token=on["plan_token"])
            install(implicit_invocation="off")
            self.assertEqual(load_manifest()["implicit_invocation"], "off")
            self.assertIn("  allow_implicit_invocation: false", self.policy().read_text(encoding="utf-8"))

    def test_implicit_invocation_legacy_upgrade_defaults_off_with_notice(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, self.environment(temp)):
            install()
            manifest_file = Path(os.environ["CODEX_COPILOT_STATE_DIR"]) / "install.json"
            manifest = load_manifest()
            manifest.pop("implicit_invocation", None)
            # Represent the previous release's true policy and matching artifact record.
            self.policy().write_text(self.policy().read_text(encoding="utf-8").replace(
                "allow_implicit_invocation: false", "allow_implicit_invocation: true"), encoding="utf-8")
            from codex_copilot.installer import artifact_fingerprint
            for item in manifest["artifacts"]:
                if item["kind"] == "skill":
                    item["fingerprint"] = artifact_fingerprint(Path(item["target"]))
            manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertIsNotNone(load_manifest())
            result = install()
            self.assertTrue(result["changed"])
            self.assertEqual(load_manifest()["implicit_invocation"], "off")
            self.assertIn("allow_implicit_invocation: false", self.policy().read_text(encoding="utf-8"))
            self.assertTrue(any("previous release allowed implicit invocation" in n for n in result["warnings"]))

    def test_implicit_invocation_symlink_on_is_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, self.environment(temp)):
            with self.assertRaisesRegex(InstallError, "copy mode"):
                install(mode="symlink", implicit_invocation="on")
            self.assertFalse(Path(os.environ["CODEX_COPILOT_STATE_DIR"]).exists())
            self.assertFalse(self.policy().exists())
            install(implicit_invocation="on")
            manifest_file = Path(os.environ["CODEX_COPILOT_STATE_DIR"]) / "install.json"
            original = manifest_file.read_bytes()
            with self.assertRaisesRegex(InstallError, "repository default"):
                install(mode="symlink")
            self.assertEqual(manifest_file.read_bytes(), original)
            self.assertTrue(all(artifact_matches(a) for a in load_manifest()["artifacts"]))

    def test_implicit_invocation_dry_run_actions_and_notice(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, self.environment(temp)):
            result = install(dry_run=True)
            self.assertIn("set implicit invocation: off", result["actions"])
            notices = " ".join(result["warnings"])
            for text in ("$codex-copilot", "read quota", "create run state", "misfires",
                         "install --implicit-invocation on|off", "doctor --json", "restart Codex Desktop"):
                self.assertIn(text, notices)
            self.assertFalse(Path(os.environ["CODEX_COPILOT_STATE_DIR"]).exists())

    def test_implicit_invocation_invalid_manifest_values_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, self.environment(temp)):
            install()
            manifest_file = Path(os.environ["CODEX_COPILOT_STATE_DIR"]) / "install.json"
            manifest = load_manifest()
            for value in (None, True, "true", [], {}):
                with self.subTest(value=value):
                    manifest_file.write_text(json.dumps({**manifest, "implicit_invocation": value}), encoding="utf-8")
                    with self.assertRaises(InstallError):
                        load_manifest()

    def test_implicit_invocation_bad_policy_rolls_back_upgrade(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, self.environment(temp)):
            from codex_copilot import installer
            source = Path(temp) / "source"
            source.mkdir()
            root = Path(__file__).resolve().parents[1]
            for name in ("src", "skill", "agents", "bin"):
                shutil.copytree(root / name, source / name, ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copy2(root / "VERSION", source / "VERSION")
            with patch.object(installer, "repo_root", return_value=source):
                install()
                manifest_file = Path(os.environ["CODEX_COPILOT_STATE_DIR"]) / "install.json"
                original_manifest = manifest_file.read_bytes()
                config = Path(os.environ["CODEX_HOME"]) / "config.toml"
                original_config = config.read_bytes()
                policy_source = source / "skill/codex-copilot/agents/openai.yaml"
                original_policy = policy_source.read_text(encoding="utf-8")
                line = "  allow_implicit_invocation: false"
                for replacement in ("", line + "\n" + line):
                    with self.subTest(replacement=replacement):
                        policy_source.write_text(original_policy.replace(line, replacement), encoding="utf-8")
                        with self.assertRaisesRegex(InstallError, "policy"):
                            install(implicit_invocation="on")
                        self.assertEqual(manifest_file.read_bytes(), original_manifest)
                        self.assertEqual(config.read_bytes(), original_config)
                        self.assertTrue(all(artifact_matches(a) for a in load_manifest()["artifacts"]))
                        self.assertIn(line, self.policy().read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
