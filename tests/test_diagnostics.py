"""Regression coverage for preference retirement, safe dispatch and RPC diagnostics."""
import json
import hashlib
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_copilot import cli, installer, quota
from codex_copilot.config_policy import config_checks
from codex_copilot.delegation import DelegationDenied, dispatch, dispatch_spec
from codex_copilot.routing import Profile, TaskLevel
from test_native import environment
from platform_support import require_symlinks
import test_native


class InstallationDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        env = environment(temp.name)
        self.env = env
        ctx = patch.dict(os.environ, env)
        ctx.start()
        self.addCleanup(ctx.stop)
        self.config = Path(env["CODEX_HOME"]) / "config.toml"
        self.config.parent.mkdir(parents=True)
        self.config.write_text('service_tier = "default"\nprivate = "secret"\n', encoding="utf-8")

    def doctor(self):
        with patch.object(cli, "get_quota", return_value=quota.unknown_snapshot("unavailable")), patch.object(
            cli.shutil, "which", return_value=None
        ):
            return cli.doctor()

    def test_preference_is_preserved_in_install_upgrade_and_uninstall(self):
        installer.install()
        result = self.doctor()
        self.assertEqual(result["installation_state"], "complete")
        self.assertFalse(result["runtime_available"])
        self.assertFalse(result["quota_status"]["available"])
        self.assertNotIn("secret", json.dumps(result))
        self.assertFalse(installer.install()["changed"])
        installer.uninstall()
        self.assertIn('service_tier = "default"', self.config.read_text(encoding="utf-8"))

    def test_unset_tier_is_not_created(self):
        self.config.write_text("", encoding="utf-8")
        installer.install()
        self.assertNotIn("service_tier", self.config.read_text(encoding="utf-8"))

    def test_direct_uninstall_of_legacy_manifest_preserves_current_tier(self):
        installer.install()
        manifest = installer.load_manifest()
        manifest["config_changes"].append({"path": "service_tier", "installed_value": "default",
                                           "previous_present": True, "previous_value": "original"})
        installer.manifest_path().write_text(json.dumps(manifest), encoding="utf-8")
        installer.uninstall()
        self.assertIn('service_tier = "default"', self.config.read_text(encoding="utf-8"))

    def test_missing_runtime_pointer_record_is_incomplete(self):
        installer.install()
        manifest = installer.load_manifest()
        pointer = Path(self.env["CODEX_COPILOT_BIN_DIR"]) / "codex-copilot.runtime.json"
        manifest["artifacts"] = [a for a in manifest["artifacts"] if a["target"] != str(pointer)]
        installer.manifest_path().write_text(json.dumps(manifest), encoding="utf-8")
        pointer.unlink()
        result = self.doctor()
        self.assertEqual(result["installation_state"], "incomplete")
        check = next(c for c in result["checks"] if c["name"] == "installation_integrity")
        self.assertTrue(any(a["target"] == str(pointer) and a["status"] == "missing_record" for a in check["artifacts"]))

    def test_symlink_agent_target_drift_and_legacy_upgrade(self):
        root = Path(self.env["CODEX_HOME"])
        require_symlinks(self, str(root))
        installer.install(mode="symlink")
        target = root / "agents/copilot-scout.toml"
        record = next(a for a in installer.load_manifest()["artifacts"] if a["target"] == str(target))
        self.assertTrue(installer.artifact_matches(record))
        changed_content = target.read_bytes() + b'\n# changed instructions\n'
        original_read = Path.read_bytes
        def changed(path):
            return changed_content if path == target else original_read(path)
        with patch.object(Path, "read_bytes", changed):
            self.assertFalse(installer.artifact_matches(record))
            with self.assertRaises(DelegationDenied):
                dispatch_spec("copilot_scout", Profile.BALANCED)
        manifest = installer.load_manifest()
        for item in manifest["artifacts"]:
            item.pop("content_fingerprint", None)
        installer.manifest_path().write_text(json.dumps(manifest), encoding="utf-8")
        self.assertFalse(installer.artifact_matches(next(a for a in manifest["artifacts"] if a["target"] == str(target))))
        self.assertTrue(installer.install(mode="symlink")["changed"])
        self.assertTrue(installer.artifact_matches(next(a for a in installer.load_manifest()["artifacts"] if a["target"] == str(target))))

    def test_symlink_content_fingerprint_without_native_privilege(self):
        installer.install()
        target = Path(self.env["CODEX_HOME"]) / "agents/copilot-scout.toml"
        record = {"kind": "agent", "target": str(target), "fingerprint": "link", "content_fingerprint": hashlib.sha256(target.read_bytes()).hexdigest()}
        original_is_symlink = Path.is_symlink
        with patch.object(Path, "is_symlink", lambda p: True if p == target else original_is_symlink(p)), patch.object(installer, "artifact_fingerprint_for", return_value="link"):
            self.assertTrue(installer.artifact_matches(record))
            target.write_bytes(target.read_bytes() + b'\n# private instructions\n')
            self.assertFalse(installer.artifact_matches(record))

    def test_legacy_tier_ownership_is_retired_with_original_record(self):
        installer.install()
        manifest = installer.load_manifest()
        record = {"path": "service_tier", "installed_value": "standard", "previous_present": True,
                  "previous_value": "original"}
        manifest["config_changes"].append(record)
        manifest["version"] = "1.0.0"
        manifest.pop("retired_config_changes", None)
        installer.manifest_path().write_text(json.dumps(manifest), encoding="utf-8")
        before = self.config.read_bytes()
        self.assertTrue(installer.install()["changed"])
        updated = installer.load_manifest()
        self.assertEqual(updated["retired_config_changes"], [record])
        self.assertFalse(any(c["path"] == "service_tier" for c in updated["config_changes"]))
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse(installer.install()["changed"])
        installer.uninstall()
        self.assertIn('service_tier = "default"', self.config.read_text(encoding="utf-8"))

    def test_retirement_rolls_back_manifest_and_configuration_on_failure(self):
        installer.install()
        manifest = installer.load_manifest()
        manifest["config_changes"].append({"path": "service_tier", "installed_value": "standard",
                                           "previous_present": False, "previous_value": None})
        installer.manifest_path().write_text(json.dumps(manifest), encoding="utf-8")
        before = installer.manifest_path().read_bytes(), self.config.read_bytes()
        original = installer._Transaction.text
        def fail_manifest(transaction, path, *args, **kwargs):
            if path == installer.manifest_path():
                raise OSError("simulated write failure")
            return original(transaction, path, *args, **kwargs)
        with patch.object(installer._Transaction, "text", fail_manifest), self.assertRaises(installer.InstallError):
            installer.install()
        self.assertEqual((installer.manifest_path().read_bytes(), self.config.read_bytes()), before)

    def test_required_setting_blocks_dispatch_even_with_override(self):
        installer.install()
        self.config.write_text(self.config.read_text(encoding="utf-8").replace("multi_agent = true", "multi_agent = false"), encoding="utf-8")
        result = self.doctor()
        self.assertEqual(result["installation_state"], "incomplete")
        blocked = [c for c in result["config_checks"] if c["blocking"]]
        self.assertEqual([c["key"] for c in blocked], ["features.multi_agent"])
        with patch("codex_copilot.delegation.get_quota") as reader, self.assertRaises(DelegationDenied):
            dispatch(run_id="11111111-1111-4111-8111-111111111111", level=TaskLevel.L3,
                     role="copilot_final_reviewer", phase="final_review", override=True)
        reader.assert_not_called()

    def test_wrong_scalar_type_does_not_pass_as_equal_setting(self):
        installer.install()
        self.config.write_text(self.config.read_text(encoding="utf-8").replace("multi_agent = true", "multi_agent = 1"), encoding="utf-8")
        self.assertTrue(next(c for c in self.doctor()["config_checks"] if c["key"] == "features.multi_agent")["blocking"])

    def test_agent_missing_and_content_changes_are_identified(self):
        installer.install()
        target = Path(self.env["CODEX_HOME"]) / "agents/copilot-scout.toml"
        target.write_text(target.read_text(encoding="utf-8") + '\n# modified prompt\n', encoding="utf-8")
        result = self.doctor()
        artifacts = next(c for c in result["checks"] if c["name"] == "installation_integrity")["artifacts"]
        self.assertEqual(next(a for a in artifacts if a["target"] == str(target))["status"], "modified_or_unreadable")
        with self.assertRaises(DelegationDenied):
            dispatch_spec("copilot_scout", Profile.BALANCED)
        target.unlink()
        result = self.doctor()
        self.assertFalse(next(c for c in result["checks"] if c["name"] == "copilot-scout.toml")["ok"])

    def test_path_missing_is_an_independent_warning(self):
        installer.install()
        with patch.dict(os.environ, {"PATH": ""}):
            result = self.doctor()
        self.assertEqual(result["installation_state"], "complete")
        check = next(c for c in result["checks"] if c["name"] == "path")
        self.assertEqual(check["severity"], "warning")
        self.assertIn("absolute launcher", check["detail"])


class RpcDiagnosticsTests(unittest.TestCase):
    def test_strict_server_waits_for_initialize_before_later_messages(self):
        script = '''import json,sys,time,threading
first=json.loads(sys.stdin.readline())
pending=[]
threading.Thread(target=lambda: pending.append(sys.stdin.readline()),daemon=True).start()
time.sleep(0.15)
if pending: sys.exit(23)
print(json.dumps({'id':first['id'],'result':{}}),flush=True)
while not pending: time.sleep(0.005)
assert json.loads(pending[0])['method']=='initialized'
read=json.loads(sys.stdin.readline())
assert read['method']=='account/rateLimits/read'
print(json.dumps({'id':read['id'],'result':{'rateLimits':{'primary':{'usedPercent':10}}}}),flush=True)
time.sleep(10)
'''
        result = test_native.PipeTests().rpc(script)
        self.assertEqual(result["rateLimits"]["primary"]["usedPercent"], 10)

    def test_initialization_error_does_not_send_follow_up_requests(self):
        script = '''import sys,json,time,threading
sys.stdin.readline()
pending=[]
threading.Thread(target=lambda: pending.append(sys.stdin.readline()),daemon=True).start()
print(json.dumps({'id':0,'error':{'message':'secret'}}),flush=True)
time.sleep(0.1)
if pending: sys.exit(25)
time.sleep(10)
'''
        with self.assertRaises(quota.QuotaReadError) as caught:
            test_native.PipeTests().rpc(script)
        self.assertEqual(caught.exception.category, "initialization_failed")
        self.assertEqual(caught.exception.phase, "initialize")
        self.assertIsNone(caught.exception.exit_code)

    def test_natural_exit_code_is_captured(self):
        with self.assertRaises(quota.QuotaReadError) as caught:
            test_native.PipeTests().rpc("import sys;sys.stdin.readline();sys.exit(17)")
        self.assertEqual(caught.exception.exit_code, 17)
        self.assertEqual(caught.exception.phase, "initialize")

    def test_eof_without_exit_does_not_report_cleanup_kill_code(self):
        script = "import sys,os,time;sys.stdin.readline();os.close(1);os.close(2);time.sleep(10)"
        with self.assertRaises(quota.QuotaReadError) as caught:
            test_native.PipeTests().rpc(script)
        self.assertIsNone(caught.exception.exit_code)

    def test_startup_errors_are_safe_and_explicit(self):
        with patch.dict(os.environ, {"CODEX_COPILOT_QUOTA_FIXTURE": ""}), patch.object(
            quota, "codex_command", side_effect=PermissionError("secret")
        ), self.assertRaises(quota.QuotaReadError) as caught:
            quota._read_rpc_result(1)
        self.assertEqual(caught.exception.phase, "startup")
        self.assertEqual(caught.exception.category, "permission_denied")
        self.assertNotIn("secret", str(caught.exception))

    def test_cache_status_and_fallback_do_not_claim_live_success(self):
        result = {"rateLimits": {"primary": {"usedPercent": 10}}}
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"CODEX_COPILOT_STATE_DIR": temp}), patch.object(
            quota, "_read_rpc_result", return_value=result
        ):
            live = quota.get_quota(refresh=True)
            self.assertTrue(live.quota_status["read_success"])
            cache = Path(temp) / "quota-cache.json"
            self.assertNotIn("quota_status", json.loads(cache.read_text(encoding="utf-8")))
            with patch.object(quota, "_read_rpc_result", side_effect=quota.QuotaReadError("process_exit", phase="initialize", exit_code=17)):
                fallback = quota.get_quota(refresh=True)
                self.assertFalse(fallback.quota_status["read_success"])
                self.assertTrue(fallback.quota_status["available"])
                self.assertEqual(fallback.quota_status["process_exit_code"], 17)
                for content, state in [(json.dumps({**json.loads(cache.read_text(encoding="utf-8")), "fetched_at":time.time()-61}), "expired"), ("bad", "invalid")]:
                    cache.write_text(content, encoding="utf-8")
                    unavailable = quota.get_quota(refresh=True)
                    self.assertFalse(unavailable.quota_status["available"])
                    self.assertEqual(unavailable.quota_status["cache_status"], state)
                cache.unlink()
                self.assertEqual(quota.get_quota(refresh=True).quota_status["cache_status"], "missing")



if __name__ == "__main__":
    unittest.main()
