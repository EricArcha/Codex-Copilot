import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_copilot import execution
from codex_copilot.delegation import DelegationDenied, complete, dispatch, dispatch_spec, trace
from codex_copilot.quota import QuotaSnapshot
from codex_copilot.routing import Profile, QuotaBand, TaskLevel


def snapshot(band: QuotaBand) -> QuotaSnapshot:
    return QuotaSnapshot(
        fetched_at=0,
        band=band.value,
        effective_remaining_percent=None,
        primary=None,
        secondary=None,
        plan_type=None,
        credits_balance=None,
        reset_credits_available=0,
        reached_type=None,
        spend_control_reached=False,
        source="test",
    )


class DelegationTests(unittest.TestCase):
    RUN_1 = "11111111-1111-4111-8111-111111111111"
    RUN_2 = "22222222-2222-4222-8222-222222222222"
    RUN_3 = "33333333-3333-4333-8333-333333333333"
    RUN_4 = "44444444-4444-4444-8444-444444444444"
    RUN_5 = "55555555-5555-4555-8555-555555555555"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        home = Path(self.temp.name) / "codex"
        agents = home / "agents"
        agents.mkdir(parents=True)
        specs = {
            "copilot-scout": ("gpt-6-luna", "low"),
            "copilot-investigator": ("gpt-6.1-sol", "medium"),
            "copilot-worker": ("gpt-6.1-sol", "medium"),
            "copilot-reviewer": ("gpt-6.1-sol", "high"),
            "copilot-final-reviewer": ("gpt-6.1-sol", "high"),
            "copilot-astra-final-reviewer": ("gpt-6-astra", "high"),
        }
        for name, (model, effort) in specs.items():
            (agents / f"{name}.toml").write_text(
                f'name = "{name}"\nmodel = "{model}"\nmodel_reasoning_effort = "{effort}"\n'
            )
        self.environment = patch.dict(
            os.environ,
            {"CODEX_HOME": str(home), "CODEX_COPILOT_STATE_DIR": str(Path(self.temp.name) / "state")},
            clear=False,
        )
        from codex_copilot.config_edit import apply_updates
        from codex_copilot.config_policy import REQUIRED_CONFIG
        (home / "config.toml").write_text(apply_updates("", REQUIRED_CONFIG)[0], encoding="utf-8")
        self.environment.start()
        self.addCleanup(self.environment.stop)
        for run_id in (self.RUN_1, self.RUN_2, self.RUN_3, self.RUN_4, self.RUN_5):
            execution.begin(run_id=run_id, normal_calls=2, worst_calls=3, call_limit=3)


    def test_green_l3_reserves_final_sol_review_and_traces_declared_config(self):
        with patch("codex_copilot.delegation.get_quota", return_value=snapshot(QuotaBand.GREEN)):
            first = dispatch(
                run_id=self.RUN_1, level=TaskLevel.L3, role="copilot_investigator", phase="exploration"
            )
            second = dispatch(
                run_id=self.RUN_1, level=TaskLevel.L3, role="copilot_final_reviewer", phase="final_review"
            )
            complete(run_id=self.RUN_1, ordinal=second["subagent_ordinal"], outcome="success")
            with self.assertRaises(DelegationDenied):
                dispatch(run_id=self.RUN_1, level=TaskLevel.L3, role="copilot_reviewer", phase="final_review")
        result = trace(self.RUN_1)
        self.assertEqual(first["subagent_model"], "gpt-6.1-sol")
        self.assertEqual(first["quota_source"], "test")
        self.assertEqual(result["compliance"], "COMPLIANT")
        self.assertEqual(result["agents"][1]["model"], "gpt-6.1-sol")
        self.assertEqual(result["agents"][1]["quota_source"], "test")
        self.assertEqual(result["agents"][1]["status"], "success")

    def test_downgrade_is_sticky_and_blocks_a_second_l3_child(self):
        with patch(
            "codex_copilot.delegation.get_quota",
            side_effect=[snapshot(QuotaBand.GREEN), snapshot(QuotaBand.YELLOW)],
        ):
            dispatch(run_id=self.RUN_2, level=TaskLevel.L3, role="copilot_scout", phase="exploration")
            with self.assertRaises(DelegationDenied):
                dispatch(
                    run_id=self.RUN_2, level=TaskLevel.L3, role="copilot_final_reviewer", phase="final_review"
                )

    def test_yellow_l3_reserves_its_only_slot_for_final_review(self):
        with patch("codex_copilot.delegation.get_quota", return_value=snapshot(QuotaBand.YELLOW)):
            with self.assertRaises(DelegationDenied):
                dispatch(run_id=self.RUN_3, level=TaskLevel.L3, role="copilot_scout", phase="exploration")
            event = dispatch(
                run_id=self.RUN_3, level=TaskLevel.L3, role="copilot_final_reviewer", phase="final_review"
            )
        self.assertEqual(event["subagent_ordinal"], 1)

    def test_unknown_role_and_missing_installed_config_are_rejected(self):
        with patch("codex_copilot.delegation.get_quota", return_value=snapshot(QuotaBand.GREEN)):
            with self.assertRaises(DelegationDenied):
                dispatch(run_id=self.RUN_4, level=TaskLevel.L1, role="other", phase="exploration")
            Path(os.environ["CODEX_HOME"]).joinpath("agents", "copilot-scout.toml").unlink()
            with self.assertRaises(DelegationDenied):
                dispatch(run_id=self.RUN_4, level=TaskLevel.L1, role="copilot_scout", phase="exploration")

    def test_explicit_override_is_visible_in_trace(self):
        grant_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        execution.grant(run_id=self.RUN_5, grant_id=grant_id, phase="final_review", category="review", user_authorized=True)
        with patch("codex_copilot.delegation.get_quota", return_value=snapshot(QuotaBand.RED)):
            dispatch(
                run_id=self.RUN_5,
                level=TaskLevel.L3,
                role="copilot_final_reviewer",
                phase="final_review",
                grant_id=grant_id,
            )
        result = trace(self.RUN_5)
        self.assertEqual(result["compliance"], "OVERRIDDEN BY USER")
        self.assertTrue(result["agents"][0]["override"])

    def test_role_phase_and_non_uuid_run_ids_are_rejected(self):
        with patch("codex_copilot.delegation.get_quota", return_value=snapshot(QuotaBand.GREEN)):
            with self.assertRaises(DelegationDenied):
                dispatch(run_id="not-a-uuid", level=TaskLevel.L1, role="copilot_scout", phase="exploration")
            with self.assertRaises(DelegationDenied):
                dispatch(run_id=self.RUN_1, level=TaskLevel.L3, role="copilot_final_reviewer", phase="exploration")

    def test_modified_agent_policy_is_rejected(self):
        path = Path(os.environ["CODEX_HOME"]) / "agents" / "copilot-reviewer.toml"
        path.write_text('model = "gpt-5.6-terra"\nmodel_reasoning_effort = "high"\n')
        with patch("codex_copilot.delegation.get_quota", return_value=snapshot(QuotaBand.YELLOW)):
            with self.assertRaises(DelegationDenied):
                dispatch(run_id=self.RUN_1, level=TaskLevel.L1, role="copilot_reviewer", phase="final_review")

    def test_distribution_agents_match_dispatch_policy(self):
        import shutil

        source = Path(__file__).resolve().parents[1] / "agents"
        target = Path(os.environ["CODEX_HOME"]) / "agents"
        for path in source.glob("copilot-*.toml"):
            shutil.copy2(path, target / path.name)
            role = path.stem.replace("-", "_")
            spec = dispatch_spec(role, Profile.PREMIUM)
            if role not in {"copilot_scout", "copilot_astra_final_reviewer"}:
                self.assertEqual(spec.model, "gpt-6.1-sol")
                self.assertIn(spec.effort, {"medium", "high"})

    def test_previous_sol_and_unsupported_efforts_require_agent_upgrade(self):
        path = Path(os.environ["CODEX_HOME"]) / "agents" / "copilot-reviewer.toml"
        for model, effort in (("gpt-6-sol", "high"), ("gpt-6.1-sol", "none"),
                              ("gpt-6.1-sol", "minimal"), ("gpt-6.1-sol", "max")):
            with self.subTest(model=model, effort=effort):
                path.write_text(f'model = "{model}"\nmodel_reasoning_effort = "{effort}"\n')
                with self.assertRaises(DelegationDenied):
                    dispatch_spec("copilot_reviewer", Profile.BALANCED)

    def test_premium_l3_uses_dedicated_astra_final_reviewer(self):
        with patch("codex_copilot.delegation.get_quota", return_value=snapshot(QuotaBand.GREEN)):
            event = dispatch(
                run_id=self.RUN_1,
                level=TaskLevel.L3,
                role="copilot_astra_final_reviewer",
                phase="final_review",
                profile=Profile.PREMIUM,
            )
        self.assertEqual(event["subagent_model"], "gpt-6-astra")
        self.assertEqual(event["profile"], "premium")

    def test_astra_fallback_uses_the_standard_sol_reviewer(self):
        with patch("codex_copilot.delegation.get_quota", return_value=snapshot(QuotaBand.YELLOW)):
            event = dispatch(
                run_id=self.RUN_1,
                level=TaskLevel.L3,
                role="copilot_reviewer",
                phase="final_review",
                astra_unavailable=True,
                profile=Profile.PREMIUM,
            )
        self.assertEqual(event["subagent_model"], "gpt-6.1-sol")


    def test_legacy_trace_stays_readable_after_explicit_recovery_and_new_calls(self):
        from codex_copilot.metrics import record
        run_id = "66666666-6666-4666-8666-666666666666"
        record(dict(event="subagent_dispatched", run_id=run_id, subagent_ordinal=1,
                    task_level="L3", quota_band="green", profile="balanced",
                    subagent_role="copilot_investigator", subagent_model="gpt-6.1-sol",
                    subagent_effort="medium", subagent_phase="exploration"))
        self.assertEqual(trace(run_id)["dispatched"], 1)
        execution.begin(run_id=run_id, normal_calls=2, worst_calls=2, call_limit=2, resume_consumed=1)
        self.assertEqual(trace(run_id)["dispatched"], 1)
        with patch("codex_copilot.delegation.get_quota", return_value=snapshot(QuotaBand.GREEN)):
            dispatch(run_id=run_id, level=TaskLevel.L3, role="copilot_final_reviewer", phase="final_review")
        result = trace(run_id)
        self.assertEqual(result["dispatched"], 2)
        self.assertTrue(result["legacy"])

    def test_unknown_then_green_retains_its_permitted_l3_fallback(self):
        with patch("codex_copilot.delegation.get_quota", side_effect=[snapshot(QuotaBand.UNKNOWN), snapshot(QuotaBand.GREEN)]):
            with self.assertRaises(DelegationDenied):
                dispatch(run_id=self.RUN_1, level=TaskLevel.L3, role="copilot_scout", phase="exploration")
            call = dispatch(run_id=self.RUN_1, level=TaskLevel.L3, role="copilot_reviewer", phase="final_review")
        self.assertEqual(call["effective_quota_band"], "unknown")
        self.assertFalse(call["override"])

    def test_bare_override_and_scoped_grants_never_bypass_role_phase(self):
        grant_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        execution.grant(run_id=self.RUN_1, grant_id=grant_id, phase="final_review", category="review", user_authorized=True)
        with patch("codex_copilot.delegation.get_quota", return_value=snapshot(QuotaBand.GREEN)):
            for role, phase in (("copilot_worker", "final_review"), ("copilot_worker", "implementation"),
                                ("copilot_investigator", "final_review")):
                with self.subTest(role=role, phase=phase), self.assertRaises(DelegationDenied):
                    dispatch(run_id=self.RUN_1, level=TaskLevel.L3, role=role, phase=phase, grant_id=grant_id)
            with self.assertRaises(DelegationDenied):
                dispatch(run_id=self.RUN_1, level=TaskLevel.L3, role="copilot_final_reviewer", phase="final_review", override=True)
        self.assertEqual(execution.status(self.RUN_1)["consumed"], 0)

    def test_metrics_failure_and_rotation_cannot_restore_child_slots(self):
        with patch("codex_copilot.delegation.get_quota", return_value=snapshot(QuotaBand.GREEN)), patch(
                "codex_copilot.delegation.record", side_effect=OSError("no metrics access")):
            dispatch(run_id=self.RUN_1, level=TaskLevel.L3, role="copilot_investigator", phase="exploration")
            dispatch(run_id=self.RUN_1, level=TaskLevel.L3, role="copilot_final_reviewer", phase="final_review")
            with self.assertRaises(DelegationDenied):
                dispatch(run_id=self.RUN_1, level=TaskLevel.L3, role="copilot_final_reviewer", phase="final_review")
        self.assertEqual(trace(self.RUN_1)["dispatched"], 2)

    def test_followup_is_pinned_and_replay_does_not_read_quota_again(self):
        request = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        session = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        grant_id = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
        with patch("codex_copilot.delegation.get_quota", return_value=snapshot(QuotaBand.GREEN)) as quota_read:
            call = dispatch(run_id=self.RUN_1, request_id=request, level=TaskLevel.L3, role="copilot_final_reviewer", phase="final_review")
            again = dispatch(run_id=self.RUN_1, request_id=request, level=TaskLevel.L3, role="copilot_final_reviewer", phase="final_review")
            self.assertTrue(again["replayed"])
            self.assertEqual(quota_read.call_count, 1)
            complete(run_id=self.RUN_1, ordinal=call["subagent_ordinal"], outcome="success", session_id=session)
            execution.grant(run_id=self.RUN_1, grant_id=grant_id, phase="exploration", category="subagent", user_authorized=True)
            with self.assertRaises(DelegationDenied):
                dispatch(run_id=self.RUN_1, level=TaskLevel.L3, role="copilot_investigator", phase="exploration", followup_id=request, grant_id=grant_id)


if __name__ == "__main__":
    unittest.main()
