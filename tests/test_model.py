import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from codex_copilot import execution as ex, model
from codex_copilot.quota import snapshot_from_result, unknown_snapshot


def uid():
    return str(uuid.uuid4())


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {"CODEX_COPILOT_STATE_DIR": self.tmp.name})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.run = uid()
        ex.begin(run_id=self.run, normal_calls=2, worst_calls=3, call_limit=3)
        ex.checkpoint(run_id=self.run, stage="offline", outcome="success", evidence_id=uid())
        self.config = patch("codex_copilot.model.require_dispatch_config")
        self.config.start()
        self.addCleanup(self.config.stop)
        self.quota = patch("codex_copilot.model.cached_quota", return_value=snapshot_from_result({"rateLimits":{"primary":{"usedPercent":10}}}))
        self.quota.start()
        self.addCleanup(self.quota.stop)

    def execute(self, **kwargs):
        options = dict(run_id=self.run, request_id=uid(), category="generation", prompt="PRIVATE PROMPT", output=StringIO())
        options.update(kwargs)
        return model.execute(**options)

    def test_model_exec_replay_never_executes_again_or_saves_content(self):
        request = uid()
        with patch("codex_copilot.model._check_features"), patch("codex_copilot.model._run", return_value=uid()) as run:
            first = self.execute(request_id=request)
            again = self.execute(request_id=request)
        self.assertTrue(first["executed"])
        self.assertFalse(again["executed"])
        self.assertEqual(run.call_count, 1)
        self.assertNotIn(b"PRIVATE PROMPT", (Path(self.tmp.name)/"execution.sqlite3").read_bytes())

    def test_failure_stays_consumed_and_does_not_reexecute(self):
        request = uid()
        with patch("codex_copilot.model._check_features", side_effect=ex.ExecutionDenied("unsupported")):
            with self.assertRaises(ex.ExecutionDenied):
                self.execute(request_id=request)
        with patch("codex_copilot.model._run") as run:
            result = self.execute(request_id=request)
        run.assert_not_called()
        self.assertEqual(result["outcome"], "failure")
        self.assertEqual(ex.status(self.run)["consumed"], 1)

    def test_data_plane_cannot_claim_independent_review_or_unknown_quota(self):
        for category in ("review", "subagent"):
            with self.assertRaises(ex.ExecutionDenied):
                self.execute(category=category)
        with patch("codex_copilot.model.cached_quota", return_value=unknown_snapshot("test")):
            with self.assertRaises(ex.ExecutionDenied):
                self.execute()
        self.assertEqual(ex.status(self.run)["consumed"], 0)

    def test_command_is_fixed_and_followup_resumes_bound_session(self):
        call = {"followup_id": None, "session_id": None}
        args = model._arguments(call, Path(self.tmp.name))
        self.assertIn("--ignore-user-config", args)
        self.assertIn("read-only", args)
        self.assertIn(model.MODEL, args)
        for feature in model.DISABLED_FEATURES:
            self.assertIn(feature, args)
        session = uid()
        args = model._arguments(dict(followup_id=uid(), session_id=session), Path(self.tmp.name))
        self.assertEqual(args[-3:], ["resume", session, "-"])

    def test_missing_isolation_features_fail_before_generation(self):
        with patch("codex_copilot.model.run_codex", return_value=SimpleNamespace(stdout="shell_tool stable true", returncode=0)):
            with self.assertRaises(ex.ExecutionDenied):
                model._check_features()

    def run_process(self, code, timeout=2, **kwargs):
        with patch("codex_copilot.model.codex_command", return_value=[sys.executable, "-c", code]):
            return model._run([], "prompt", StringIO(), timeout, **kwargs)

    def test_real_process_receipt_completes_and_stderr_is_discarded(self):
        session = uid()
        events = [{"type":"thread.started","thread_id":session}, {"type":"turn.completed","usage":{"input_tokens":1}}]
        code = "import sys; sys.stdin.read(); sys.stderr.write('SECRET'*100000); print(" + repr("\n".join(json.dumps(x) for x in events)) + ")"
        self.assertEqual(self.run_process(code), session)

    def test_native_pascal_case_message_items_are_not_mistaken_for_tools(self):
        session = uid()
        events = [{"type":"thread.started","thread_id":session},
                  {"type":"item.completed","item":{"type":"Reasoning","id":"0","summary_text":[]}},
                  {"type":"item.completed","item":{"type":"AgentMessage","id":"1","text":"OK"}},
                  {"type":"turn.completed"}]
        code = "import sys; sys.stdin.read(); print(" + repr("\n".join(json.dumps(x) for x in events)) + ")"
        self.assertEqual(self.run_process(code), session)

    def test_real_process_timeout_and_unexpected_tool_event_are_rejected(self):
        with self.assertRaisesRegex(ex.ExecutionDenied, "timed out"):
            self.run_process("import time; time.sleep(5)", timeout=0.1)
        code = 'import sys; sys.stdin.read(); print(\'{"type":"item.started","item":{"type":"command_execution"}}\')'
        with self.assertRaisesRegex(ex.ExecutionDenied, "tool activity"):
            self.run_process(code)

    def test_real_process_session_mismatch_and_incomplete_turn_fail(self):
        code = "import sys; sys.stdin.read(); print(" + repr(json.dumps({"type":"thread.started","thread_id":uid()})) + ")"
        with self.assertRaisesRegex(ex.ExecutionDenied, "different session"):
            self.run_process(code, expected_session=uid())
        with self.assertRaisesRegex(ex.ExecutionDenied, "incomplete"):
            self.run_process("import sys; sys.stdin.read()")

    def test_post_spawn_timeout_preserves_unknown_session_and_blocks_resume(self):
        request, session = uid(), uid()
        code = "import sys,time; sys.stdin.read(); print(" + repr(json.dumps({"type":"thread.started","thread_id":session})) + ", flush=True); time.sleep(5)"
        with patch("codex_copilot.model._check_features"), patch("codex_copilot.model.codex_command", return_value=[sys.executable,"-c",code]):
            with self.assertRaises(model.ModelCallError):
                self.execute(request_id=request, timeout=0.1)
        call = ex.status(self.run)["calls"][0]
        self.assertEqual(call["outcome"], "unknown")
        self.assertEqual(call["session_id"], session)
        with self.assertRaises(ex.ExecutionDenied):
            model.reserve(run_id=self.run, request_id=uid(), category="generation", followup_id=request)

    def test_post_spawn_keyboard_interrupt_preserves_unknown_session(self):
        class InterruptingOutput(StringIO):
            def write(self, text):
                raise KeyboardInterrupt()
        request, session = uid(), uid()
        code = "import sys,time; sys.stdin.read(); print(" + repr(json.dumps({"type":"thread.started","thread_id":session})) + ", flush=True); time.sleep(5)"
        with patch("codex_copilot.model._check_features"), patch("codex_copilot.model.codex_command", return_value=[sys.executable,"-c",code]):
            with self.assertRaises(KeyboardInterrupt):
                self.execute(request_id=request, output=InterruptingOutput())
        call = ex.status(self.run)["calls"][0]
        self.assertEqual((call["outcome"], call["session_id"]), ("unknown", session))
        with self.assertRaises(ex.ExecutionDenied):
            model.reserve(run_id=self.run, request_id=uid(), category="generation", followup_id=request)

    def test_prompt_limits_and_timeout_validate_before_reservation(self):
        for options in ({"prompt":" "}, {"timeout":float("nan")}, {"prompt":"x"*(4*1024*1024+1)}):
            with self.assertRaises(ex.ExecutionDenied):
                self.execute(**options)
        self.assertEqual(ex.status(self.run)["consumed"], 0)
