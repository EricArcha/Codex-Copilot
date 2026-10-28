import json
import os
import sqlite3
import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from codex_copilot import execution as ex
from codex_copilot.metrics import metrics_path, record
from codex_copilot.quota import Window, unknown_snapshot
from dataclasses import replace


def uid():
    return str(uuid.uuid4())


def quota(band="green", used=10, reset=1000, source="app-server"):
    return replace(unknown_snapshot("test"), band=band, source=source, error=None,
                   primary=Window(used, 100-used, 300, reset))


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {"CODEX_COPILOT_STATE_DIR": self.tmp.name})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.run = uid()

    def begin(self, **kwargs):
        options = dict(run_id=self.run, normal_calls=3, worst_calls=6, call_limit=6)
        options.update(kwargs)
        return ex.begin(**options)

    def reserve(self, **kwargs):
        options = dict(run_id=self.run, request_id=uid(), kind="model", category="generation",
                       phase="evaluation", snapshot=quota(), role="data_model", model="gpt-6.1-sol",
                       effort="medium", level="L2", profile="balanced")
        options.update(kwargs)
        if options["role"] == "copilot_reviewer" and "effort" not in kwargs:
            options["effort"] = "high"
        return ex.reserve(**options)

    def preflight(self):
        return ex.checkpoint(run_id=self.run, stage="offline", outcome="success", evidence_id=uid())

    def finish(self, call, **kwargs):
        return ex.complete(run_id=self.run, request_id=call["request_id"], outcome="success", **kwargs)

    def grant(self, **kwargs):
        options = dict(run_id=self.run, grant_id=uid(), phase="evaluation", category="generation", user_authorized=True)
        options.update(kwargs)
        return ex.grant(**options)

    def test_missing_or_partial_budget_permits_only_offline(self):
        ex.begin(run_id=self.run)
        self.preflight()
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve()
        with self.assertRaises(ex.ExecutionDenied):
            ex.begin(run_id=uid(), call_limit=4)

    def test_preflight_is_required_and_unknown_quota_never_expands_bulk(self):
        self.begin()
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve()
        self.preflight()
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve(snapshot=unknown_snapshot("test"))
        self.assertEqual(ex.status(self.run)["consumed"], 0)
        self.assertEqual(ex.status(self.run)["effective_band"], "unknown")

    def test_green_does_not_override_total_budget_or_final_reserve(self):
        self.begin(call_limit=2, reserve_calls=1)
        self.preflight()
        call = self.reserve()
        self.finish(call)
        grant = self.grant(count=10)
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve(grant_id=grant["grant_id"])
        review = self.reserve(kind="subagent", role="copilot_reviewer", category="review", phase="final_review")
        ex.complete(run_id=self.run, request_id=review["request_id"], outcome="failure")
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve(kind="subagent", role="copilot_reviewer", category="review", phase="final_review")

    def test_grant_is_scoped_single_use_and_cannot_reset_budget(self):
        self.begin()
        self.preflight()
        grant = self.grant()
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve(snapshot=quota("critical"), grant_id=grant["grant_id"], category="repair")
        self.reserve(snapshot=quota("critical"), grant_id=grant["grant_id"])
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve(grant_id=grant["grant_id"])
        self.assertEqual(self.grant(grant_id=grant["grant_id"])["remaining"], 0)
        with self.assertRaises(ex.ExecutionDenied):
            self.begin(call_limit=100)

    def test_expired_grant_and_authorization_declaration(self):
        self.begin()
        self.preflight()
        with self.assertRaises(ex.ExecutionDenied):
            self.grant(user_authorized=False)
        with patch("codex_copilot.execution.time.time", return_value=100):
            grant = self.grant(expires_in=1)
        with patch("codex_copilot.execution.time.time", return_value=102):
            with self.assertRaises(ex.ExecutionDenied):
                self.reserve(grant_id=grant["grant_id"])

    def test_restrictive_observation_survives_denial_and_natural_window_reset(self):
        self.begin()
        self.preflight()
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve(snapshot=quota("critical"))
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve(snapshot=quota("green", reset=2000))
        state = ex.status(self.run)
        self.assertEqual((state["current_band"], state["effective_band"]), ("green", "critical"))
        grant = self.grant()
        self.reserve(grant_id=grant["grant_id"])
        self.assertEqual(ex.status(self.run)["consumed"], 1)

    def test_idempotent_reservation_claim_and_completion_survive_reopen(self):
        self.begin()
        self.preflight()
        request = uid()
        call = self.reserve(request_id=request)
        self.assertTrue(self.reserve(request_id=request)["replayed"])
        self.assertTrue(ex.claim_model(run_id=self.run, request_id=request))
        self.assertFalse(ex.claim_model(run_id=self.run, request_id=request))
        session = uid()
        self.finish(call, session_id=session)
        self.finish(call, session_id=session)
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve(request_id=request, category="repair")
        with self.assertRaises(ex.ExecutionDenied):
            ex.complete(run_id=self.run, request_id=request, outcome="failure")
        self.assertEqual(ex.status(self.run)["consumed"], 1)

    def test_parallel_reservations_never_overspend(self):
        self.begin(call_limit=1)
        self.preflight()
        def attempt(_):
            try:
                self.reserve()
                return True
            except ex.ExecutionDenied:
                return False
        with ThreadPoolExecutor(max_workers=6) as pool:
            self.assertEqual(sum(pool.map(attempt, range(12))), 1)
        self.assertEqual(ex.status(self.run)["consumed"], 1)

    def test_rotation_does_not_restore_budget(self):
        self.begin(call_limit=1)
        self.preflight()
        self.reserve()
        record({"run_id": self.run, "event": "test"})
        metrics_path().unlink()
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve()

    def test_unknown_corrupt_or_unwritable_state_fails_closed(self):
        path = Path(self.tmp.name) / "execution.sqlite3"
        path.write_bytes(b"unknown user file")
        with self.assertRaises(ex.ExecutionDenied):
            self.begin()
        self.assertEqual(path.read_bytes(), b"unknown user file")
        path.unlink()
        self.begin()
        with patch("codex_copilot.execution.sqlite3.connect", side_effect=sqlite3.OperationalError("secret /path")):
            with self.assertRaisesRegex(ex.ExecutionDenied, "Execution state unavailable") as error:
                self.reserve()
            self.assertNotIn("secret", str(error.exception))
        with closing(sqlite3.connect(path)) as db, db:
            data = json.loads(db.execute("SELECT payload FROM runs").fetchone()[0])
            data["consumed"] = -1
            db.execute("UPDATE runs SET payload=?", (json.dumps(data),))
        with self.assertRaises(ex.ExecutionDenied):
            ex.status(self.run)

    def test_failed_cancelled_unknown_calls_remain_consumed(self):
        self.begin(call_limit=3)
        self.preflight()
        for outcome in ("failure", "cancelled", "unknown"):
            call = self.reserve()
            ex.complete(run_id=self.run, request_id=call["request_id"], outcome=outcome)
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve()

    def test_session_followup_cannot_relabel_or_overlap(self):
        self.begin()
        self.preflight()
        call = self.reserve()
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve(followup_id=call["request_id"])
        self.finish(call, session_id=uid())
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve(followup_id=call["request_id"], effort="low")
        next_call = self.reserve(followup_id=call["request_id"])
        self.assertEqual(next_call["session_id"], ex.status(self.run)["calls"][0]["session_id"])
        with self.assertRaises(ex.ExecutionDenied):
            self.finish(next_call, session_id=uid())

    def test_writer_slot_cannot_be_reopened_by_grant(self):
        self.begin()
        first = self.reserve(kind="subagent", role="copilot_worker", phase="implementation", category="subagent")
        grant = self.grant(phase="implementation", category="subagent")
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve(kind="subagent", role="copilot_worker", phase="implementation", category="subagent", grant_id=grant["grant_id"])
        ex.complete(run_id=self.run, request_id=first["request_id"], outcome="unknown")
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve(kind="subagent", role="copilot_worker", phase="implementation", category="subagent", grant_id=grant["grant_id"])

    def worker(self, role, **kwargs):
        options = dict(kind="subagent", role=role, phase="implementation", category="subagent",
                       model="gpt-6.1-terra" if role == "copilot_terra_worker" else "gpt-6.1-sol", level="L1")
        options.update(kwargs)
        return self.reserve(**options)

    def test_sol_and_terra_workers_share_unresolved_writer_slot_even_with_grant(self):
        roles = ("copilot_worker", "copilot_terra_worker")
        for first_role in roles:
            for second_role in roles:
                with self.subTest(first=first_role, second=second_role):
                    self.run = uid()
                    self.begin()
                    first = self.worker(first_role)
                    grant = self.grant(phase="implementation", category="subagent")
                    for outcome in (None, "unknown"):
                        if outcome:
                            ex.complete(run_id=self.run, request_id=first["request_id"], outcome=outcome)
                        with self.subTest(outcome=outcome), self.assertRaisesRegex(ex.ExecutionDenied, "writer slot"):
                            self.worker(second_role, grant_id=grant["grant_id"])
                    self.assertEqual(ex.status(self.run)["consumed"], 1)
                    self.assertEqual(ex.status(self.run)["grants"][0]["remaining"], 1)

    def test_parallel_sol_and_terra_requests_claim_only_one_writer(self):
        self.begin()
        def attempt(role):
            try:
                self.worker(role)
                return True
            except ex.ExecutionDenied:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(attempt, ("copilot_worker", "copilot_terra_worker"))), 1)
        self.assertEqual(ex.status(self.run)["consumed"], 1)

    def test_terra_followup_pins_session_and_retains_review_reserve(self):
        self.begin(call_limit=3, reserve_calls=1)
        first = self.worker("copilot_terra_worker")
        self.finish(first, session_id=uid())
        grant = self.grant(phase="implementation", category="subagent")
        with self.assertRaisesRegex(ex.ExecutionDenied, "Follow-up cannot change"):
            self.worker("copilot_worker", followup_id=first["request_id"], grant_id=grant["grant_id"])
        continuation = self.worker("copilot_terra_worker", followup_id=first["request_id"],
                                   grant_id=grant["grant_id"])
        self.assertEqual(continuation["session_id"], ex.status(self.run)["calls"][0]["session_id"])
        self.finish(continuation, session_id=continuation["session_id"])
        extra = self.grant(phase="implementation", category="subagent")
        with self.assertRaisesRegex(ex.ExecutionDenied, "closing reserve"):
            self.worker("copilot_terra_worker", grant_id=extra["grant_id"])
        self.assertEqual(ex.status(self.run)["consumed"], 2)

    def test_failed_terra_worker_releases_writer_without_refunding_attempt(self):
        self.begin()
        first = self.worker("copilot_terra_worker")
        ex.complete(run_id=self.run, request_id=first["request_id"], outcome="failure")
        grant = self.grant(phase="implementation", category="subagent")
        self.worker("copilot_worker", grant_id=grant["grant_id"])
        self.assertEqual(ex.status(self.run)["consumed"], 2)

    def review(self, **kwargs):
        options = dict(kind="subagent", role="copilot_reviewer", effort="high",
                       category="review", phase="final_review")
        options.update(kwargs)
        return self.reserve(**options)

    def test_second_fresh_final_review_is_denied_for_green_levels_and_profiles(self):
        for level, profile, role, fallback in (
            ("L1", "balanced", "copilot_reviewer", False),
            ("L2", "balanced", "copilot_reviewer", False),
            ("L3", "balanced", "copilot_final_reviewer", False),
            ("L3", "conservative", "copilot_final_reviewer", False),
            ("L3", "premium", "copilot_astra_final_reviewer", False),
            ("L3", "premium", "copilot_reviewer", True),
        ):
            with self.subTest(level=level, profile=profile, role=role):
                self.run = uid()
                self.begin()
                options = dict(level=level, profile=profile, role=role,
                               model="gpt-6-astra" if role == "copilot_astra_final_reviewer" else "gpt-6.1-sol",
                               astra_unavailable=fallback)
                call = self.review(**options)
                self.finish(call, session_id=uid())
                with self.assertRaisesRegex(ex.ExecutionDenied, "This run already used its final-review session; recheck with a follow-up of that reviewer session or obtain a bounded user grant"):
                    self.review(**options)
                self.assertEqual(ex.status(self.run)["child_consumed"], 1)

    def test_green_reviewer_followup_uses_second_slot(self):
        for level, role in (("L1", "copilot_reviewer"), ("L2", "copilot_reviewer"),
                            ("L3", "copilot_final_reviewer")):
            with self.subTest(level=level):
                self.run = uid()
                self.begin()
                call = self.review(level=level, role=role)
                session = uid()
                self.finish(call, session_id=session)
                followup = self.review(level=level, role=role, followup_id=call["request_id"])
                self.assertEqual(followup["session_id"], session)
                self.assertEqual(ex.status(self.run)["child_consumed"], 2)

    def test_investigator_then_final_review_leaves_no_followup_slot(self):
        self.begin()
        scout = self.reserve(kind="subagent", category="subagent", role="copilot_investigator",
                             phase="exploration", level="L3")
        self.finish(scout)
        review = self.review(level="L3", role="copilot_final_reviewer")
        self.finish(review, session_id=uid())
        with self.assertRaisesRegex(ex.ExecutionDenied, "cumulative child cap reached"):
            self.review(level="L3", role="copilot_final_reviewer", followup_id=review["request_id"])

    def test_bounded_grant_allows_second_fresh_final_review(self):
        self.begin()
        self.finish(self.review())
        grant = self.grant(phase="final_review", category="review")
        call = self.review(grant_id=grant["grant_id"])
        self.assertIsNone(call["followup_id"])
        self.assertEqual(ex.status(self.run)["grants"][0]["remaining"], 0)

    def test_legacy_consumption_retains_existing_final_slot(self):
        self.begin(resume_consumed=1)
        call = self.review(level="L3", role="copilot_final_reviewer")
        self.assertEqual(call["child_ordinal"], 2)
        self.finish(call, session_id=uid())
        with self.assertRaises(ex.ExecutionDenied):
            self.review(level="L3", role="copilot_final_reviewer", followup_id=call["request_id"])

    def test_stages_require_real_calls_paired_scoring_and_bounded_batches(self):
        self.begin(comparison=True, smoke_calls=2, pilot_calls=2, batch_calls=2, call_limit=10)
        self.preflight()
        with self.assertRaises(ex.ExecutionDenied):
            ex.checkpoint(run_id=self.run, stage="smoke", outcome="success", evidence_id=uid())
        self.finish(self.reserve())
        self.finish(self.reserve(category="scoring"))
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve()
        ex.checkpoint(run_id=self.run, stage="smoke", outcome="success", evidence_id=uid(), scored=True)
        self.finish(self.reserve())
        self.finish(self.reserve(category="scoring"))
        with self.assertRaises(ex.ExecutionDenied):
            ex.checkpoint(run_id=self.run, stage="pilot", outcome="success", evidence_id=uid())
        ex.checkpoint(run_id=self.run, stage="pilot", outcome="success", evidence_id=uid(), paired=True, scored=True)
        self.finish(self.reserve())
        self.finish(self.reserve(category="scoring"))
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve()
        ex.checkpoint(run_id=self.run, stage="batch", outcome="success", evidence_id=uid(), paired=True, scored=True)
        self.finish(self.reserve())

    def test_two_blockers_pause_until_new_offline_diagnosis_evidence(self):
        self.begin()
        self.preflight()
        for _ in range(2):
            ex.checkpoint(run_id=self.run, stage="smoke", outcome="blocked", blocker="protocol")
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve()
        self.preflight()
        self.assertEqual(ex.status(self.run)["stage"], "smoke")
        self.reserve()

    def test_paused_stage_cannot_be_unpaused_by_different_blocker_or_old_success(self):
        self.begin()
        self.preflight()
        self.finish(self.reserve())
        for _ in range(2):
            ex.checkpoint(run_id=self.run, stage="smoke", outcome="blocked", blocker="protocol")
        ex.checkpoint(run_id=self.run, stage="smoke", outcome="blocked", blocker="runtime")
        self.assertTrue(ex.status(self.run)["paused"])
        with self.assertRaises(ex.ExecutionDenied):
            ex.checkpoint(run_id=self.run, stage="smoke", outcome="success", evidence_id=uid())
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve()

    def test_repeated_pause_resume_with_the_same_confirmed_count(self):
        self.begin(resume_consumed=0)
        for _ in range(3):
            ex.close(run_id=self.run, outcome="paused")
            self.assertEqual(self.begin(resume_consumed=0)["status"], "active")

    def test_unknown_outcome_blocks_stage_expansion_and_completed_close(self):
        self.begin()
        ex.checkpoint(run_id=self.run, stage="offline", outcome="success", evidence_id=uid(), engineering="passed", review="passed")
        self.finish(self.reserve())
        call = self.reserve()
        ex.complete(run_id=self.run, request_id=call["request_id"], outcome="unknown")
        with self.assertRaises(ex.ExecutionDenied):
            ex.checkpoint(run_id=self.run, stage="smoke", outcome="success", evidence_id=uid(), engineering="passed", review="passed")
        # Acceptance fields alone cannot make an unresolved run complete.
        with self.assertRaises(ex.ExecutionDenied):
            ex.close(run_id=self.run, outcome="completed")

    def test_durable_resume_does_not_depend_on_metrics_readability(self):
        self.begin()
        ex.close(run_id=self.run, outcome="paused")
        with patch("codex_copilot.metrics.records_for_run", side_effect=OSError("metrics unreadable")):
            self.assertEqual(self.begin(resume_consumed=0)["status"], "active")
            with self.assertRaises(ex.ExecutionDenied):
                self.begin(run_id=uid())

    def test_status_opens_sqlite_read_only(self):
        self.begin()
        connect = sqlite3.connect
        with patch("codex_copilot.execution.sqlite3.connect", wraps=connect) as spy:
            ex.status(self.run)
        self.assertIn("?mode=ro", spy.call_args.args[0])

    def test_engineering_success_does_not_complete_comparison(self):
        self.begin(comparison=True)
        ex.checkpoint(run_id=self.run, stage="offline", outcome="success", evidence_id=uid(), engineering="passed", review="passed")
        with self.assertRaises(ex.ExecutionDenied):
            ex.close(run_id=self.run, outcome="completed")
        self.assertFalse(ex.status(self.run)["publication_eligible"])
        ex.close(run_id=self.run, outcome="paused")
        state = self.begin(resume_consumed=0, comparison=True)
        self.assertEqual(state["status"], "active")
        self.assertEqual(state["effect"], "pending")

    def test_legacy_trace_requires_confirmed_count_and_never_lowers_it(self):
        record({"event": "subagent_dispatched", "run_id": self.run, "subagent_ordinal": 90,
                "quota_band": "critical", "profile": "balanced", "task_level": "L3"})
        with self.assertRaises(ex.ExecutionDenied):
            self.begin(call_limit=100)
        with self.assertRaises(ex.ExecutionDenied):
            self.begin(call_limit=100, resume_consumed=89)
        state = self.begin(call_limit=100, resume_consumed=90)
        self.assertEqual(state["consumed"], 90)
        self.assertEqual(state["effective_band"], "critical")

    def test_observed_guard_reuses_start_snapshot_and_never_overrides_limit(self):
        with patch("codex_copilot.execution.cached_quota", return_value=quota(used=10)):
            self.begin(quota_limit_pp=10, quota_reserve_pp=2)
        self.preflight()
        self.reserve(snapshot=quota(used=17))
        grant = self.grant()
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve(snapshot=quota(used=18), grant_id=grant["grant_id"])
        # Closing review may use the reserve, but not the absolute observed limit.
        self.reserve(kind="subagent", role="copilot_reviewer", category="review", phase="final_review", snapshot=quota(used=19))
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve(kind="subagent", role="copilot_reviewer", category="review", phase="final_review", snapshot=quota(used=20))

    def test_observed_guard_rejects_cross_window_without_rebasing(self):
        with patch("codex_copilot.execution.cached_quota", return_value=quota()):
            self.begin(quota_limit_pp=10)
        self.preflight()
        with self.assertRaises(ex.ExecutionDenied):
            self.reserve(snapshot=quota(reset=2000))
        self.assertEqual(ex.status(self.run)["consumed"], 0)

    def test_budget_state_does_not_start_measurement_or_store_content(self):
        with patch("codex_copilot.execution.cached_quota") as cached:
            self.begin()
            cached.assert_not_called()
        self.assertFalse((Path(self.tmp.name)/"measurement.json").exists())
        with self.assertRaises(ex.ExecutionDenied):
            ex.checkpoint(run_id=self.run, stage="offline", outcome="success", evidence_id="private prompt")
        raw = (Path(self.tmp.name)/"execution.sqlite3").read_bytes()
        self.assertNotIn(b"private prompt", raw)
