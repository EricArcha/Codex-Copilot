import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from codex_copilot.cli import doctor, main
from codex_copilot.installer import CONFIG_UPDATES, SYMLINK_RISK_WARNING, install
from codex_copilot.metrics import record
from codex_copilot.quota import unknown_snapshot


class CliTests(unittest.TestCase):
    def environment(self, root: str) -> dict[str, str]:
        base = Path(root)
        return {
            "CODEX_HOME": str(base / ".codex"),
            "CODEX_COPILOT_SKILLS_HOME": str(base / ".agents" / "skills"),
            "CODEX_COPILOT_BIN_DIR": str(base / ".local" / "bin"),
            "CODEX_COPILOT_SHARE_DIR": str(base / ".local" / "share" / "codex-copilot"),
            "CODEX_COPILOT_STATE_DIR": str(base / ".codex-copilot"),
        }

    def test_doctor_accepts_copy_install_and_warns_for_symlink_agents(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            with patch.dict(os.environ, env, clear=False), patch(
                "codex_copilot.cli.shutil.which", return_value=None
            ), patch("codex_copilot.cli.get_quota", return_value=unknown_snapshot("test")):
                install()
                copied = doctor()
                copied_checks = {check["name"]: check for check in copied["checks"]}
                self.assertTrue(copied_checks["installation_integrity"]["ok"])
                self.assertIn("regular file", copied_checks["copilot-scout.toml"]["detail"])
                self.assertFalse(any(SYMLINK_RISK_WARNING in warning for warning in copied["warnings"]))

                install(mode="symlink")
                linked = doctor()
                linked_checks = {check["name"]: check for check in linked["checks"]}
                self.assertTrue(linked_checks["installation_integrity"]["ok"])
                self.assertIn("symlink", linked_checks["copilot-scout.toml"]["detail"])
                self.assertTrue(any(SYMLINK_RISK_WARNING in warning for warning in linked["warnings"]))

    def test_doctor_reports_unavailable_quota_as_a_warning(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            env["PATH"] = f"{env['CODEX_COPILOT_BIN_DIR']}{os.pathsep}{os.environ.get('PATH', '')}"
            responses = iter(
                (
                    SimpleNamespace(stdout="codex-cli 0.147.0", stderr="", returncode=0),
                    SimpleNamespace(stdout="Logged in using ChatGPT", stderr="", returncode=0),
                )
            )
            with patch.dict(os.environ, env, clear=False), patch(
                "codex_copilot.cli.shutil.which", return_value="/usr/local/bin/codex"
            ), patch("codex_copilot.cli.subprocess.run", side_effect=responses), patch(
                "codex_copilot.cli.get_quota", return_value=unknown_snapshot("timed out")
            ):
                install()
                result = doctor()
                self.assertTrue(result["ok"])
                self.assertTrue(any("Quota check unavailable" in warning for warning in result["warnings"]))

    def test_symlink_dry_run_prints_risk_warning(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            with patch.dict(os.environ, env, clear=False):
                stdout, stderr = StringIO(), StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    code = main(["install", "--mode", "symlink", "--dry-run"])
                self.assertEqual(code, 0)
                self.assertIn(SYMLINK_RISK_WARNING, stderr.getvalue())

    def test_install_dry_run_shows_managed_config_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            stdout, stderr = StringIO(), StringIO()
            with patch.dict(os.environ, env, clear=False), redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["install", "--dry-run"])
            self.assertEqual(code, 0)
            self.assertIn("Managed settings", stdout.getvalue())
            self.assertIn("features.multi_agent: <unset> -> true", stdout.getvalue())
            self.assertIn("Configuration backup directory", stdout.getvalue())
            for path in CONFIG_UPDATES:
                self.assertIn(path, stdout.getvalue())
            self.assertFalse(Path(env["CODEX_COPILOT_STATE_DIR"]).exists())

    def test_install_refuses_non_interactive_without_yes(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            stdout, stderr = StringIO(), StringIO()
            with patch.dict(os.environ, env, clear=False), redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["install"])
            self.assertEqual(code, 2)
            self.assertIn("without --yes", stderr.getvalue())
            self.assertFalse(Path(env["CODEX_COPILOT_STATE_DIR"]).exists())

    def test_install_can_be_confirmed_with_yes_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            with patch.dict(os.environ, env, clear=False):
                first_out, first_err = StringIO(), StringIO()
                with redirect_stdout(first_out), redirect_stderr(first_err):
                    self.assertEqual(main(["install", "--yes"]), 0)
                self.assertIn("Managed settings", first_out.getvalue())
                self.assertTrue((Path(env["CODEX_HOME"]) / "config.toml").exists())

                second_out, second_err = StringIO(), StringIO()
                with redirect_stdout(second_out), redirect_stderr(second_err):
                    self.assertEqual(main(["install"]), 0)
                self.assertIn("Already installed; no changes.", second_out.getvalue())
                self.assertNotIn("without --yes", second_err.getvalue())

    def test_copy_to_symlink_preview_lists_the_distribution_removal(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            with patch.dict(os.environ, env, clear=False):
                install(mode="copy")
                distribution = Path(env["CODEX_COPILOT_SHARE_DIR"])
                stdout, stderr = StringIO(), StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    self.assertEqual(main(["install", "--mode", "symlink", "--dry-run"]), 0)
                self.assertIn("remove obsolete copied distribution", stdout.getvalue())
                self.assertTrue(distribution.exists())

                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    self.assertEqual(main(["install", "--mode", "symlink", "--yes"]), 0)
                self.assertFalse(distribution.exists())

    def test_install_decline_leaves_no_state(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            stdout, stderr = StringIO(), StringIO()
            interactive_stdin = SimpleNamespace(isatty=lambda: True)
            with (
                patch.dict(os.environ, env, clear=False),
                patch("codex_copilot.cli.sys.stdin", interactive_stdin),
                patch("codex_copilot.cli.builtins.input", return_value=""),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                code = main(["install"])
            self.assertEqual(code, 2)
            self.assertIn("Installation cancelled", stderr.getvalue())
            self.assertFalse(Path(env["CODEX_COPILOT_STATE_DIR"]).exists())

    def test_doctor_explains_recovery_when_the_installed_skill_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            with patch.dict(os.environ, env, clear=False), patch(
                "codex_copilot.cli.shutil.which", return_value=None
            ), patch("codex_copilot.cli.get_quota", return_value=unknown_snapshot("test")):
                install()
                shutil.rmtree(Path(env["CODEX_COPILOT_SKILLS_HOME"]) / "codex-copilot")
                result = doctor()
            self.assertTrue(any("installation residue" in warning for warning in result["warnings"]))

    def test_status_json_with_fixture(self):
        fixture = Path(__file__).parent / "fixtures" / "quota-green.json"
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(
                os.environ,
                {
                    "CODEX_COPILOT_STATE_DIR": temp,
                    "CODEX_COPILOT_QUOTA_FIXTURE": str(fixture),
                },
                clear=False,
            ):
                output = StringIO()
                with redirect_stdout(output):
                    code = main(["status", "--json", "--refresh"])
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(output.getvalue())["band"], "green")

    def test_launch_dry_run_selects_expected_model(self):
        fixture = Path(__file__).parent / "fixtures" / "quota-green.json"
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(
                os.environ,
                {
                    "CODEX_COPILOT_STATE_DIR": temp,
                    "CODEX_COPILOT_QUOTA_FIXTURE": str(fixture),
                },
                clear=False,
            ):
                output = StringIO()
                with redirect_stdout(output):
                    code = main(["launch", "--level", "complex", "--dry-run"])
                self.assertEqual(code, 0)
                data = json.loads(output.getvalue())
                self.assertEqual(data["command"][2], "gpt-5.6-terra")
                self.assertEqual(data["route"]["max_subagents"], 2)

    def test_trace_json_reports_retained_subagent_run(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"CODEX_COPILOT_STATE_DIR": temp}, clear=False):
                record(
                    {
                        "event": "subagent_dispatched",
                        "run_id": "11111111-1111-4111-8111-111111111111",
                        "task_level": "L1",
                        "effective_quota_band": "yellow",
                        "subagent_role": "copilot_reviewer",
                        "subagent_ordinal": 1,
                        "subagent_model": "gpt-5.6-terra",
                        "subagent_effort": "high",
                        "subagent_phase": "final_review",
                    }
                )
                output = StringIO()
                with redirect_stdout(output):
                    code = main(["trace", "--json"])
                self.assertEqual(code, 0)
                data = json.loads(output.getvalue())
                self.assertEqual(data["run_id"], "11111111-1111-4111-8111-111111111111")
                self.assertEqual(data["agents"][0]["role"], "copilot_reviewer")

    def test_trace_without_subagents_is_a_clear_non_secret_error(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"CODEX_COPILOT_STATE_DIR": temp}, clear=False):
                output = StringIO()
                with redirect_stdout(output):
                    code = main(["trace"])
                self.assertEqual(code, 1)
                self.assertEqual(output.getvalue().strip(), "No subagent trace found.")


if __name__ == "__main__":
    unittest.main()
