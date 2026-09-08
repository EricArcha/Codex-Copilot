import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_copilot.quota import get_quota, snapshot_from_result


class QuotaTests(unittest.TestCase):
    def test_uses_lower_remaining_window(self):
        result = {
            "rateLimits": {
                "primary": {"usedPercent": 20, "windowDurationMins": 300},
                "secondary": {"usedPercent": 75, "windowDurationMins": 10080},
                "planType": "plus",
            }
        }
        snapshot = snapshot_from_result(result)
        self.assertEqual(snapshot.effective_remaining_percent, 25)
        self.assertEqual(snapshot.band, "red")

    def test_reached_state_is_critical(self):
        result = {
            "rateLimits": {
                "primary": {"usedPercent": 1},
                "rateLimitReachedType": "weekly",
            }
        }
        self.assertEqual(snapshot_from_result(result).band, "critical")

    def test_null_windows_are_unknown(self):
        self.assertEqual(snapshot_from_result({"rateLimits": {}}).band, "unknown")

    def test_credits_and_api_key_style_empty_limits(self):
        result = {
            "rateLimits": {"primary": {"usedPercent": 5}, "planType": "plus"},
            "rateLimitResetCredits": {"availableCount": 3},
        }
        self.assertEqual(snapshot_from_result(result).reset_credits_available, 3)
        self.assertEqual(snapshot_from_result({"rateLimits": {}}).source, "app-server")

    def test_timeout_login_failure_and_unavailable_are_unknown(self):
        failures = [
            TimeoutError("timed out"),
            RuntimeError("not logged in"),
            FileNotFoundError("codex missing"),
        ]
        for failure in failures:
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as temp:
                with patch.dict(os.environ, {"CODEX_COPILOT_STATE_DIR": temp}, clear=False), patch(
                    "codex_copilot.quota._read_rpc_result", side_effect=failure
                ):
                    snapshot = get_quota(refresh=True)
                    self.assertEqual(snapshot.band, "unknown")
                    self.assertIn(str(failure), snapshot.error)

    def test_fixture_and_cache(self):
        root = Path(__file__).parent
        fixture = root / "fixtures" / "quota-green.json"
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(
                os.environ,
                {
                    "CODEX_COPILOT_STATE_DIR": temp,
                    "CODEX_COPILOT_QUOTA_FIXTURE": str(fixture),
                },
                clear=False,
            ):
                snapshot = get_quota(refresh=True)
                self.assertEqual(snapshot.band, "green")
                self.assertEqual(snapshot.reset_credits_available, 2)
                self.assertTrue((Path(temp) / "quota-cache.json").exists())

    def test_refresh_failure_uses_recent_successful_cache(self):
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
                get_quota(refresh=True)
            with patch.dict(os.environ, {"CODEX_COPILOT_STATE_DIR": temp}, clear=False), patch(
                "codex_copilot.quota._read_rpc_result", side_effect=TimeoutError("timed out")
            ):
                snapshot = get_quota(refresh=True)
        self.assertEqual(snapshot.band, "green")
        self.assertEqual(snapshot.source, "cache-fallback")
        self.assertEqual(snapshot.error, "Fresh quota read failed: timed out")

    def test_refresh_failure_rejects_stale_or_non_successful_cache(self):
        fixture = Path(__file__).parent / "fixtures" / "quota-green.json"
        for mutation in (
            lambda raw: raw.update(fetched_at=0),
            lambda raw: raw.update(source="unavailable"),
        ):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                with patch.dict(
                    os.environ,
                    {
                        "CODEX_COPILOT_STATE_DIR": temp,
                        "CODEX_COPILOT_QUOTA_FIXTURE": str(fixture),
                    },
                    clear=False,
                ):
                    get_quota(refresh=True)
                cache = Path(temp) / "quota-cache.json"
                raw = json.loads(cache.read_text())
                mutation(raw)
                cache.write_text(json.dumps(raw))
                with patch.dict(os.environ, {"CODEX_COPILOT_STATE_DIR": temp}, clear=False), patch(
                    "codex_copilot.quota._read_rpc_result", side_effect=TimeoutError("timed out")
                ):
                    snapshot = get_quota(refresh=True)
                self.assertEqual(snapshot.band, "unknown")
                self.assertEqual(snapshot.source, "unavailable")

    def test_non_refresh_cache_is_labeled_as_cached(self):
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
                get_quota(refresh=True)
            with patch.dict(os.environ, {"CODEX_COPILOT_STATE_DIR": temp}, clear=False), patch(
                "codex_copilot.quota._read_rpc_result", side_effect=AssertionError("must not refresh")
            ):
                snapshot = get_quota()
        self.assertEqual(snapshot.source, "cache")


if __name__ == "__main__":
    unittest.main()
