import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from codex_copilot.measurement import begin, compare, enabled, end, set_enabled, settings_path
from codex_copilot.metrics import metrics_path, summarize
from codex_copilot.quota import QuotaSnapshot, Window


def snapshot(primary: float, secondary: float, *, primary_reset: int = 1000,
             secondary_reset: int = 2000) -> QuotaSnapshot:
    return QuotaSnapshot(
        fetched_at=1, band="green", effective_remaining_percent=None,
        primary=Window(primary, 100-primary, 300, primary_reset),
        secondary=Window(secondary, 100-secondary, 10080, secondary_reset),
        plan_type="plus", credits_balance=None, reset_credits_available=0,
        reached_type=None, spend_control_reached=False, source="app-server",
    )


class MeasurementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"CODEX_COPILOT_STATE_DIR": self.temp.name})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.temp.cleanup)
        self.project = str(Path(self.temp.name) / "project")

    def test_default_off_does_not_read_quota_or_record(self):
        self.assertFalse(enabled())
        with patch("codex_copilot.measurement.get_quota") as quota, patch(
            "codex_copilot.quota.cached_quota"
        ) as cached:
            result = begin(run_id=str(uuid.uuid4()), variant="skill", task_level="L1",
                           task_kind="feature", root_model="gpt-6-sol", project=self.project,
                           if_enabled=True)
        self.assertFalse(result["recorded"])
        quota.assert_not_called()
        cached.assert_not_called()
        self.assertFalse(metrics_path().exists())

    def test_on_off_and_explicit_one_time_run(self):
        set_enabled(True)
        self.assertTrue(enabled())
        set_enabled(False)
        self.assertFalse(enabled())
        run_id = str(uuid.uuid4())
        with patch("codex_copilot.measurement.get_quota", return_value=snapshot(10, 20)) as quota:
            first = begin(run_id=run_id, variant="baseline", task_level="L2",
                          task_kind="bugfix", root_model="gpt-6-sol", project=self.project)
            second = begin(run_id=run_id, variant="baseline", task_level="L2",
                           task_kind="bugfix", root_model="gpt-6-sol", project=self.project)
        self.assertTrue(first["recorded"])
        self.assertFalse(second["recorded"])
        quota.assert_called_once()
        self.assertEqual(len(metrics_path().read_text().splitlines()), 1)
        with self.assertRaises(ValueError):
            begin(run_id=run_id, variant="skill", task_level="L2", task_kind="bugfix",
                  root_model="gpt-6-sol", project=self.project)

    def test_skill_begin_reuses_cache_and_end_reads_once(self):
        run_id = str(uuid.uuid4())
        with patch("codex_copilot.quota.cached_quota", return_value=snapshot(10, 20)) as cached, patch(
            "codex_copilot.measurement.get_quota", return_value=snapshot(14, 21)
        ) as quota:
            begin(run_id=run_id, variant="skill", task_level="L2", task_kind="bugfix",
                  root_model="gpt-6-sol", project=self.project)
            self.assertEqual(quota.call_count, 0)
            self.assertEqual(cached.call_count, 1)
            first = end(run_id=run_id, outcome="success")
            second = end(run_id=run_id, outcome="success")
        self.assertTrue(first["recorded"])
        self.assertFalse(second["recorded"])
        with self.assertRaises(ValueError):
            end(run_id=run_id, outcome="failure")
        quota.assert_called_once()
        result = summarize(365)
        self.assertEqual(result["tasks"], 1)
        self.assertEqual(result["complete_samples"], 1)
        self.assertEqual(result["average_primary_delta_observed"]["gpt-6-sol:unknown"], 4)
        saved = metrics_path().read_text()
        self.assertNotIn(self.project, saved)

    def test_missing_quota_and_window_reset_are_incomplete(self):
        run_id = str(uuid.uuid4())
        with patch("codex_copilot.quota.cached_quota", return_value=None), patch(
            "codex_copilot.measurement.get_quota", return_value=snapshot(2, 3)
        ):
            begin(run_id=run_id, variant="skill", task_level="L1", task_kind="maintenance",
                  root_model="gpt-6-sol", project=self.project)
            end(run_id=run_id, outcome="success")
        self.assertEqual(summarize(365)["complete_samples"], 0)

        second = str(uuid.uuid4())
        begin(run_id=second, variant="baseline", task_level="L1", task_kind="maintenance",
              root_model="gpt-6-sol", project=self.project,
              primary_used=10, secondary_used=10, primary_reset=1000, secondary_reset=2000)
        end(run_id=second, outcome="success", primary_used=1, secondary_used=11,
            primary_reset=3000, secondary_reset=2000)
        self.assertEqual(summarize(365)["complete_samples"], 0)
        with self.assertRaises(ValueError):
            compare(run_id, second)

    def test_paired_comparison_reports_observed_difference_only(self):
        skill = str(uuid.uuid4())
        baseline = str(uuid.uuid4())
        for run_id, variant, start, finish in (
            (skill, "skill", (10, 20), (13, 21)),
            (baseline, "baseline", (30, 30), (35, 32)),
        ):
            begin(run_id=run_id, variant=variant, task_level="L2", task_kind="feature",
                  root_model="gpt-6-sol", project=self.project,
                  primary_used=start[0], secondary_used=start[1],
                  primary_reset=1000, secondary_reset=2000)
            end(run_id=run_id, outcome="success", primary_used=finish[0],
                secondary_used=finish[1], primary_reset=1000, secondary_reset=2000)
        result = compare(skill, baseline)
        self.assertEqual(result["windows"]["primary"]["baseline_minus_skill_pp"], 2)
        self.assertEqual(result["windows"]["secondary"]["baseline_minus_skill_pp"], 1)
        self.assertIn("Observational", result["note"])
        self.assertEqual(summarize(365)["tasks"], 2)

    def test_invalid_content_cannot_become_run_id_or_category(self):
        with self.assertRaises(ValueError):
            begin(run_id="my task", variant="skill", task_level="L2", task_kind="feature",
                  root_model="gpt-6-sol", project=self.project)
        with self.assertRaises(ValueError):
            begin(run_id=str(uuid.uuid4()), variant="skill", task_level="L2",
                  task_kind="fix my private project", root_model="gpt-6-sol", project=self.project)
        self.assertFalse(metrics_path().exists())

    def test_setting_does_not_follow_symlink_or_replace_unknown_file(self):
        sentinel = Path(self.temp.name) / "sentinel"
        sentinel.write_text("keep")
        path = settings_path()
        path.symlink_to(sentinel)
        with self.assertRaises(ValueError):
            set_enabled(True)
        self.assertEqual(sentinel.read_text(), "keep")
        path.unlink()
        path.write_text("unknown user data")
        with self.assertRaises(ValueError):
            set_enabled(True)
        self.assertEqual(path.read_text(), "unknown user data")

    def test_partial_app_snapshot_is_saved_but_not_compared(self):
        run_id = str(uuid.uuid4())
        begin(run_id=run_id, variant="skill", task_level="L1", task_kind="bugfix",
              root_model="gpt-6-sol", project=self.project,
              primary_used=10, primary_reset=1000)
        end(run_id=run_id, outcome="success", primary_used=12, primary_reset=1000)
        self.assertEqual(summarize(365)["complete_samples"], 0)
        self.assertIn("codex-app-provided-partial", metrics_path().read_text())

    def test_uppercase_run_id_is_normalized_for_follow_up(self):
        run_id = str(uuid.uuid4())
        begin(run_id=run_id.upper(), variant="skill", task_level="L1", task_kind="bugfix",
              root_model="gpt-6-sol", project=self.project,
              primary_used=10, secondary_used=10, primary_reset=1000, secondary_reset=2000)
        result = end(run_id=run_id, outcome="success", primary_used=11,
                     secondary_used=11, primary_reset=1000, secondary_reset=2000)
        self.assertEqual(result["event"]["run_id"], run_id)


if __name__ == "__main__":
    unittest.main()
