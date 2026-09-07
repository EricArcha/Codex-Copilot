import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from codex_copilot.cli import main
from codex_copilot.metrics import record


class CliTests(unittest.TestCase):
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
