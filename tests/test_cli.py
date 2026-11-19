import json
import os
import shutil
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tests.platform_support import require_symlinks

from codex_copilot.cli import doctor, main
from codex_copilot.installer import (
    CONFIG_UPDATES,
    IMPLICIT_INVOCATION_RELOAD_NOTICE,
    RESTART_NOTICE,
    SYMLINK_RISK_WARNING,
    install,
    load_manifest,
)
from codex_copilot.metrics import record
from codex_copilot.quota import QuotaSnapshot, unknown_snapshot
from codex_copilot.routing import QuotaBand, TaskLevel, route_for


class CliTests(unittest.TestCase):
    def test_live_quota_cache_warning_is_not_reported_as_unavailable(self):
        from dataclasses import replace
        from codex_copilot.cli import _status_text
        from codex_copilot.quota import snapshot_from_result
        snapshot = replace(snapshot_from_result({"rateLimits": {"primary": {"usedPercent": 10}}}),
                           error="Cache unavailable", error_category="state_write_failed", retryable=True)
        text = _status_text(snapshot)
        self.assertIn("Quota warning", text)
        self.assertNotIn("Quota unavailable", text)
        self.assertIn("state_write_failed", text)

    def test_measure_cli_is_opt_in_and_supports_one_time_comparison(self):
        import uuid
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"CODEX_COPILOT_STATE_DIR": temp}, clear=False):
                output = StringIO()
                with redirect_stdout(output):
                    self.assertEqual(main(["measure", "status", "--json"]), 0)
                self.assertFalse(json.loads(output.getvalue())["measurement_enabled"])
                skill = str(uuid.uuid4())
                baseline = str(uuid.uuid4())
                for run_id, variant, start, finish in (
                    (skill, "skill", 10, 12), (baseline, "baseline", 30, 34)
                ):
                    start_args = ["measure", "begin", "--run-id", run_id, "--variant", variant,
                                  "--task-level", "L1", "--task-kind", "bugfix",
                                  "--root-model", "gpt-6-sol", "--project", temp,
                                  "--primary-used", str(start), "--secondary-used", "5",
                                  "--primary-reset", "1000", "--secondary-reset", "2000"]
                    end_args = ["measure", "end", "--run-id", run_id, "--outcome", "success",
                                "--primary-used", str(finish), "--secondary-used", "6",
                                "--primary-reset", "1000", "--secondary-reset", "2000"]
                    with redirect_stdout(StringIO()):
                        self.assertEqual(main(start_args), 0)
                        self.assertEqual(main(end_args), 0)
                output = StringIO()
                with redirect_stdout(output):
                    self.assertEqual(main(["measure", "compare", "--skill-run", skill,
                                           "--baseline-run", baseline, "--json"]), 0)
                self.assertEqual(json.loads(output.getvalue())["windows"]["primary"]["baseline_minus_skill_pp"], 2)

    def yellow_snapshot(self) -> QuotaSnapshot:
        return QuotaSnapshot(
            fetched_at=0,
            band="yellow",
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

                require_symlinks(self, temp)
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
            with patch.dict(os.environ, env, clear=False), patch("codex_copilot.cli.sys.stdin", SimpleNamespace(isatty=lambda: False)), redirect_stdout(stdout), redirect_stderr(stderr):
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
                self.assertEqual(first_err.getvalue().count("Optional allowance measurement"), 1)
                self.assertEqual(first_err.getvalue().count(RESTART_NOTICE), 1)
                self.assertTrue((Path(env["CODEX_HOME"]) / "config.toml").exists())

                second_out, second_err = StringIO(), StringIO()
                with redirect_stdout(second_out), redirect_stderr(second_err):
                    self.assertEqual(main(["install"]), 0)
                self.assertIn("Already installed; no changes.", second_out.getvalue())
                self.assertNotIn("without --yes", second_err.getvalue())
                self.assertNotIn(RESTART_NOTICE, second_err.getvalue())

    def test_interactive_install_asks_about_the_model_after_installing(self):
        for answer, recommendation, effort in (
            ("", "gpt-6.2-sol", "medium"),
            ("yes", "gpt-6.1-terra", "low"),
        ):
            with self.subTest(answer=answer), tempfile.TemporaryDirectory() as temp, patch.dict(
                os.environ, self.environment(temp)
            ), patch("codex_copilot.installer.route_for", return_value=replace(
                route_for(QuotaBand.UNKNOWN, TaskLevel.L1), root_model=recommendation, root_effort=effort
            )), patch("codex_copilot.installer._supports_default_model", return_value=True) as support, patch(
                "codex_copilot.cli.sys.stdin", SimpleNamespace(isatty=lambda: True)
            ), redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                config = Path(os.environ["CODEX_HOME"]) / "config.toml"
                config.parent.mkdir()
                config.write_text('model = "gpt-6.1-sol"\nmodel_reasoning_effort = "high"\n')

                def reply(question):
                    if question.startswith("Proceed with"):
                        self.assertIsNone(load_manifest())
                        return "yes"
                    self.assertIsNotNone(load_manifest())
                    self.assertEqual(tomllib.loads(config.read_text())["model"], "gpt-6.1-sol")
                    self.assertIn("this installation's recommendation", question)
                    self.assertIn(f"{recommendation} with {effort} reasoning", question)
                    self.assertTrue(question.endswith("[y/N] "))
                    return answer

                with patch("builtins.input", side_effect=reply) as ask:
                    self.assertEqual(main(["install"]), 0)
                    self.assertEqual(ask.call_count, 2)
                saved = tomllib.loads(config.read_text())
                self.assertEqual(saved["model"], recommendation if answer else "gpt-6.1-sol")
                self.assertEqual(saved["model_reasoning_effort"], effort if answer else "high")
                support.assert_called_with(recommendation, effort)

    def test_install_yes_keeps_the_model_and_explicit_opt_in_can_run_later(self):
        out = StringIO()
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, self.environment(temp)), patch(
            "codex_copilot.installer._supports_default_model", return_value=True
        ) as catalog, patch("codex_copilot.installer.cached_quota", return_value=SimpleNamespace(band="future")), patch(
            "builtins.input"
        ) as ask, redirect_stdout(out), redirect_stderr(StringIO()):
            config = Path(os.environ["CODEX_HOME"]) / "config.toml"
            self.assertEqual(main(["install", "--yes"]), 0)
            ask.assert_not_called()
            catalog.assert_not_called()
            self.assertNotIn("model", tomllib.loads(config.read_text()))
            self.assertIn("--set-default-model", out.getvalue())
            self.assertNotIn("after restarting Codex Desktop", out.getvalue())
            self.assertEqual(main(["install", "--dry-run", "--set-default-model"]), 0)
            self.assertNotIn("after restarting Codex Desktop", out.getvalue())
            self.assertNotIn("model", tomllib.loads(config.read_text()))
            self.assertEqual(main(["install", "--yes", "--set-default-model"]), 0)
            saved = tomllib.loads(config.read_text())
            self.assertEqual(saved["model"], "gpt-6.2-sol")
            self.assertEqual(saved["model_reasoning_effort"], "medium")
            self.assertEqual(out.getvalue().count("after restarting Codex Desktop"), 1)
            ask.assert_not_called()

    def test_model_opt_in_reuses_existing_symlink_mode(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, self.environment(temp)), patch(
            "codex_copilot.installer._supports_default_model", return_value=True
        ), redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            require_symlinks(self, temp)
            self.assertEqual(main(["install", "--mode", "symlink", "--yes"]), 0)
            self.assertEqual(main(["install", "--yes", "--set-default-model"]), 0)
            self.assertEqual(load_manifest()["mode"], "symlink")
            config = Path(os.environ["CODEX_HOME"]) / "config.toml"
            self.assertEqual(tomllib.loads(config.read_text())["model"], "gpt-6.2-sol")

    def test_desktop_install_previews_and_applies_only_the_shown_recommendation(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, self.environment(temp)), patch(
            "codex_copilot.installer._supports_default_model", return_value=True
        ), patch("builtins.input") as ask, redirect_stderr(StringIO()):
            config = Path(os.environ["CODEX_HOME"]) / "config.toml"
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["install", "--yes"]), 0)

            def preview():
                stdout = StringIO()
                with redirect_stdout(stdout):
                    self.assertEqual(main(["default-model", "--json"]), 0)
                return json.loads(stdout.getvalue())

            plan = preview()
            self.assertEqual((plan["status"], plan["model"], plan["effort"]), ("available", "gpt-6.2-sol", "medium"))
            self.assertNotIn("model", tomllib.loads(config.read_text()))
            config.write_text('model = "user-choice"\n' + config.read_text())
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["default-model", "--apply-plan", plan["plan_token"], "--json"]), 1)
            self.assertEqual(tomllib.loads(config.read_text())["model"], "user-choice")

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["default-model", "--apply-plan", preview()["plan_token"], "--json"]), 0)
            self.assertEqual(json.loads(stdout.getvalue())["status"], "changed")
            self.assertEqual(tomllib.loads(config.read_text())["model"], "gpt-6.2-sol")
            self.assertEqual(preview()["status"], "current")
            ask.assert_not_called()

    def test_install_implicit_invocation_flag_reaches_preview_and_confirmation(self):
        for setting in ("on", "off"):
            with self.subTest(setting=setting), tempfile.TemporaryDirectory() as temp:
                with patch.dict(os.environ, self.environment(temp)), patch(
                    "codex_copilot.cli.install", wraps=install
                ) as calls, redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    self.assertEqual(main(["install", "--implicit-invocation", setting, "--yes"]), 0)
                self.assertEqual(len(calls.call_args_list), 2)
                self.assertTrue(all(c.kwargs["implicit_invocation"] == setting for c in calls.call_args_list))

    def test_install_implicit_invocation_notice_prints_once_for_dry_real_and_repeat(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, self.environment(temp)):
            for args, expected_reload in (
                (["install", "--dry-run"], None),
                (["install", "--yes"], RESTART_NOTICE),
                (["install", "--implicit-invocation", "on", "--yes"], IMPLICIT_INVOCATION_RELOAD_NOTICE),
                (["install"], None),
            ):
                stdout, stderr = StringIO(), StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    self.assertEqual(main(args), 0)
                self.assertEqual(stderr.getvalue().count("Explicit invocation is $codex-copilot"), 1)
                for notice in (RESTART_NOTICE, IMPLICIT_INVOCATION_RELOAD_NOTICE):
                    self.assertEqual(stderr.getvalue().count(notice), int(notice == expected_reload))

    def test_doctor_json_reports_implicit_invocation_on_off_and_unknown(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, self.environment(temp)), patch(
            "codex_copilot.cli.shutil.which", return_value=None
        ), patch("codex_copilot.cli.get_quota", return_value=unknown_snapshot("test")):
            def reported():
                output = StringIO()
                with redirect_stdout(output):
                    main(["doctor", "--json"])
                return json.loads(output.getvalue())["implicit_invocation"]
            self.assertEqual(reported(), "unknown")
            install()
            self.assertEqual(reported(), "off")
            install(implicit_invocation="on")
            self.assertEqual(reported(), "on")
            manifest_file = Path(os.environ["CODEX_COPILOT_STATE_DIR"]) / "install.json"
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            manifest.pop("implicit_invocation")
            manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(reported(), "unknown")

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

                require_symlinks(self, temp)
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
                    **self.environment(temp),
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
                    **self.environment(temp),
                    "CODEX_COPILOT_QUOTA_FIXTURE": str(fixture),
                },
                clear=False,
            ):
                install()
                output = StringIO()
                with redirect_stdout(output):
                    code = main(["launch", "--level", "complex", "--dry-run"])
                self.assertEqual(code, 0)
                data = json.loads(output.getvalue())
                self.assertEqual(data["command"][2], "gpt-6.2-sol")
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
                        "subagent_model": "gpt-6-sol",
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

    def test_delegate_accepts_the_astra_fallback_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.environment(temp)
            with patch.dict(os.environ, env, clear=False), patch(
                "codex_copilot.delegation.get_quota", return_value=self.yellow_snapshot()
            ):
                install()
                from codex_copilot.execution import begin
                begin(run_id="11111111-1111-4111-8111-111111111111", normal_calls=1, worst_calls=1, call_limit=1)
                denied = StringIO()
                with redirect_stderr(denied):
                    self.assertEqual(main([
                        "_delegate", "dispatch", "--run-id", "11111111-1111-4111-8111-111111111111",
                        "--request-id", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                        "--task-level", "L3", "--role", "copilot_reviewer", "--phase", "final_review",
                        "--profile", "premium",
                    ]), 1)
                output = StringIO()
                with redirect_stdout(output):
                    code = main([
                        "_delegate", "dispatch", "--run-id", "11111111-1111-4111-8111-111111111111",
                        "--request-id", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                        "--task-level", "L3", "--role", "copilot_reviewer", "--phase", "final_review",
                        "--astra-unavailable", "--profile", "premium",
                    ])
                self.assertEqual(code, 0)

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
