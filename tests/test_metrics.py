import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_copilot.metrics import metrics_path, project_hash, record, summarize


class MetricsTests(unittest.TestCase):
    def test_records_only_allowlisted_fields_and_hashes_project(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"CODEX_COPILOT_STATE_DIR": temp}, clear=False):
                hashed = project_hash("/private/example/project")
                record(
                    {
                        "event": "complete",
                        "surface": "test",
                        "project_hash": hashed,
                        "task_level": "L1",
                        "root_model": "gpt-5.6-terra",
                        "root_effort": "medium",
                        "primary_delta_observed": 2.0,
                        "outcome": "success",
                    }
                )
                text = metrics_path().read_text()
                self.assertNotIn("/private/example/project", text)
                self.assertIn(hashed, text)
                self.assertEqual(summarize(30)["records"], 1)
                self.assertEqual(
                    summarize(30)["average_primary_delta_observed"]["gpt-5.6-terra:medium"],
                    2.0,
                )

    def test_rejects_prompt_or_path_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"CODEX_COPILOT_STATE_DIR": temp}, clear=False):
                with self.assertRaises(ValueError):
                    record({"event": "bad", "prompt": "secret"})
                with self.assertRaises(ValueError):
                    record({"event": "bad", "project_path": "/secret"})

    def test_rotates_bounded_local_log(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"CODEX_COPILOT_STATE_DIR": temp}, clear=False), patch(
                "codex_copilot.metrics.MAX_BYTES", 1
            ):
                record({"event": "first"})
                record({"event": "second"})
                self.assertTrue(metrics_path().with_name("runs.jsonl.1").exists())


if __name__ == "__main__":
    unittest.main()
