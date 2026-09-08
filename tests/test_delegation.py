import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_copilot.delegation import DelegationDenied, complete, dispatch, trace
from codex_copilot.quota import QuotaSnapshot
from codex_copilot.routing import QuotaBand, TaskLevel


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
            "copilot-scout": ("gpt-5.6-luna", "low"),
            "copilot-investigator": ("gpt-5.6-terra", "medium"),
            "copilot-worker": ("gpt-5.6-terra", "medium"),
            "copilot-reviewer": ("gpt-5.6-terra", "high"),
            "copilot-final-reviewer": ("gpt-5.6-sol", "high"),
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
        self.environment.start()
        self.addCleanup(self.environment.stop)

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
        self.assertEqual(first["subagent_model"], "gpt-5.6-terra")
        self.assertEqual(first["quota_source"], "test")
        self.assertEqual(result["compliance"], "COMPLIANT")
        self.assertEqual(result["agents"][1]["model"], "gpt-5.6-sol")
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
        with patch("codex_copilot.delegation.get_quota", return_value=snapshot(QuotaBand.RED)):
            dispatch(
                run_id=self.RUN_5,
                level=TaskLevel.L3,
                role="copilot_final_reviewer",
                phase="final_review",
                override=True,
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
        path.write_text('model = "gpt-5.6-sol"\nmodel_reasoning_effort = "high"\n')
        with patch("codex_copilot.delegation.get_quota", return_value=snapshot(QuotaBand.YELLOW)):
            with self.assertRaises(DelegationDenied):
                dispatch(run_id=self.RUN_1, level=TaskLevel.L1, role="copilot_reviewer", phase="final_review")


if __name__ == "__main__":
    unittest.main()
