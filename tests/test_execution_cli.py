import json
import os
import tempfile
import unittest
import uuid
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from codex_copilot.cli import main, _parser
from codex_copilot import execution
from codex_copilot.release_identity import check


def uid():
    return str(uuid.uuid4())


class ExecutionCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {"CODEX_COPILOT_STATE_DIR": self.tmp.name})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.run = uid()

    def invoke(self, args):
        output, error = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            code = main(args)
        return code, json.loads(output.getvalue()) if output.getvalue() else None, error.getvalue()

    def test_lifecycle_and_bounded_user_grant(self):
        code, state, _ = self.invoke(["run", "begin", "--run-id", self.run, "--normal-calls", "1", "--worst-calls", "2", "--call-limit", "2", "--reserve-calls", "1"])
        self.assertEqual(code, 0)
        self.assertEqual(state["consumed"], 0)
        grant = uid()
        args = ["grant", "--run-id", self.run, "--grant-id", grant, "--phase", "final_review", "--category", "review"]
        self.assertEqual(self.invoke(args)[0], 1)
        self.assertEqual(self.invoke(args + ["--user-authorized"])[1]["remaining"], 1)
        self.assertEqual(self.invoke(["run", "checkpoint", "--run-id", self.run, "--stage", "offline", "--outcome", "success", "--evidence-id", uid(), "--engineering", "passed", "--review", "passed"])[0], 0)
        self.assertEqual(self.invoke(["run", "close", "--run-id", self.run, "--outcome", "completed"])[0], 0)

    def test_model_command_rejects_arbitrary_overrides(self):
        args = ["model", "exec", "--run-id", self.run, "--request-id", uid(), "--category", "generation"]
        for extra in (["--model", "other"], ["-c", "anything=true"], ["--sandbox", "danger-full-access"]):
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                _parser().parse_args(args + extra)

    def test_uuid_errors_never_persist_user_content(self):
        self.assertEqual(self.invoke(["run", "begin", "--run-id", "user private task"])[0], 1)
        self.assertFalse((Path(self.tmp.name)/"execution.sqlite3").exists())

    def test_project_identity_does_not_fall_back_to_global_values_or_change_config(self):
        with patch("codex_copilot.release_identity.subprocess.run") as run:
            run.return_value.returncode = 1
            run.return_value.stdout = ""
            self.assertFalse(check()["ready"])
            self.assertEqual(run.call_count, 2)
            for call in run.call_args_list:
                self.assertIn("--local", call.args[0])
                self.assertNotIn("--global", call.args[0])

    def test_project_identity_checks_effective_author_and_committer_without_exposing_them(self):
        from types import SimpleNamespace
        responses = ["Project", "project@example.invalid", "Project <project@example.invalid> 1 +0000", "Other <private@example.invalid> 1 +0000"]
        with patch("codex_copilot.release_identity.subprocess.run", side_effect=[SimpleNamespace(returncode=0, stdout=x) for x in responses]):
            result = check()
        self.assertFalse(result["ready"])
        self.assertNotIn("private@example", json.dumps(result))
