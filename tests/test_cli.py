import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from codex_copilot.cli import doctor, main
from codex_copilot.installer import SYMLINK_RISK_WARNING, install
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
