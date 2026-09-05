import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from codex_copilot.cli import main


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


if __name__ == "__main__":
    unittest.main()

