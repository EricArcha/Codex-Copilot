import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from codex_copilot import installer, user_path
from codex_copilot.cli import _launch, _version_tuple, doctor
from codex_copilot.paths import repo_root, skills_home
from codex_copilot.process import codex_command
from codex_copilot.quota import _read_rpc_result, get_quota, unknown_snapshot


def environment(root):
    base = Path(root) / "中文 path"
    return {"CODEX_HOME": str(base / "codex"), "CODEX_COPILOT_SKILLS_HOME": str(base / "skills"),
            "CODEX_COPILOT_BIN_DIR": str(base / "bin"), "CODEX_COPILOT_SHARE_DIR": str(base / "runtime"),
            "CODEX_COPILOT_STATE_DIR": str(base / "state")}


class PipeTests(unittest.TestCase):
    def test_malformed_nested_quota_degrades_to_unknown(self):
        cases = [{"rateLimitsByLimitId": []}, {"rateLimits": []}, {"rateLimits": {"primary": []}},
                 {"rateLimits": {"credits": []}}, {"rateLimitResetCredits": []},
                 {"rateLimits": {"primary": {"usedPercent": "nan"}}}]
        for result in cases:
            with self.subTest(result=result), tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"CODEX_COPILOT_STATE_DIR": temp}), patch("codex_copilot.quota._read_rpc_result", return_value=result):
                self.assertEqual(get_quota(refresh=True).band, "unknown")
    def rpc(self, script, timeout=2):
        processes = []
        original = subprocess.Popen

        def start(*args, **kwargs):
            process = original(*args, **kwargs)
            processes.append(process)
            return process

        with patch.dict(os.environ, {"CODEX_COPILOT_QUOTA_FIXTURE": ""}), patch(
            "codex_copilot.quota.codex_command", return_value=[sys.executable, "-u", "-c", script]
        ), patch("codex_copilot.quota.subprocess.Popen", side_effect=start):
            try:
                return _read_rpc_result(timeout)
            finally:
                self.assertTrue(processes)
                self.assertIsNotNone(processes[0].poll())
                self.assertTrue(processes[0].stdin.closed)
                self.assertTrue(processes[0].stdout.closed)
                self.assertFalse(any(t.name == "codex-copilot-quota-reader" for t in threading.enumerate()))

    def test_buffered_consecutive_responses_and_unicode(self):
        script = "import sys,json,time; [sys.stdin.readline() for _ in range(3)]; print(json.dumps({'id':0,'result':{}})); print(json.dumps({'method':'notice'})); print(json.dumps({'id':1,'result':{'name':'中文','rateLimits':{}}})); time.sleep(10)"
        self.assertEqual(self.rpc(script)["name"], "中文")

    def test_timeout_and_partial_line_have_bounded_cleanup(self):
        for script in ("import time; time.sleep(10)", "import sys,time; sys.stdout.write('{'); sys.stdout.flush(); time.sleep(10)"):
            start = time.monotonic()
            with self.subTest(script=script), self.assertRaises(TimeoutError):
                self.rpc(script, timeout=0.3)
            self.assertLess(time.monotonic() - start, 3)

    def test_eof_rpc_errors_and_invalid_responses(self):
        scripts = ["pass", "print('{\"id\":1,\"error\":{\"message\":\"failed\"}}')",
                   "print('{\"id\":0,\"error\":{}}')", "print('invalid json')", "print('[]')",
                   "print('{\"id\":1}')", "print('{\"id\":1,\"result\":null}')"]
        for script in scripts:
            with self.subTest(script=script), self.assertRaises((RuntimeError, ValueError)):
                self.rpc(script)

    def test_notification_flood_still_times_out(self):
        with self.assertRaises(TimeoutError):
            self.rpc("import json; msg=json.dumps({'method':'notice'});\nwhile True: print(msg,flush=True)", timeout=0.3)

    def test_cleanup_error_still_closes_pipes_and_reader(self):
        from codex_copilot import process_tree
        original_stop = process_tree.stop

        def fail_after_stop(proc, job):
            original_stop(proc, job)
            raise OSError("cleanup error")

        with patch("codex_copilot.quota.process_tree.stop", side_effect=fail_after_stop), self.assertRaisesRegex(OSError, "cleanup error"):
            self.rpc("print('{\"id\":1,\"result\":{}}')")

    def test_child_holding_stdout_is_reaped_even_after_parent_eof(self):
        script = "import subprocess,sys; subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)']); print('{\"id\":1,\"result\":{}}',flush=True)"
        started = time.monotonic()
        self.assertEqual(self.rpc(script), {})
        self.assertLess(time.monotonic() - started, 3)


class NativeInstallTests(unittest.TestCase):
    def test_dry_run_upgrade_and_custom_runtime_location(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)):
            base = Path(temp)
            installer.install(dry_run=True)
            self.assertEqual(list(base.iterdir()), [])
            installer.install()
            manifest = installer.load_manifest()
            self.assertEqual(len([a for a in manifest["artifacts"] if a["kind"] == "agent"]), 6)
            command = [sys.executable, str(Path(os.environ["CODEX_COPILOT_BIN_DIR"]) / ("codex-copilot.py" if os.name == "nt" else "codex-copilot")), "--version"]
            response = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=10)
            self.assertEqual(response.returncode, 0, response.stderr)
            self.assertIn("0.1.1", response.stdout)
            self.assertFalse(installer.install()["changed"])
            with patch("codex_copilot.installer.VERSION", "0.1.2"):
                self.assertTrue(installer.install()["changed"])
            self.assertTrue(Path(installer.load_manifest()["backup_dir"]).is_dir())
            installer.uninstall()
            self.assertFalse(installer.manifest_path().exists())

    def test_unmanaged_distribution_and_modified_artifact_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)):
            runtime = Path(os.environ["CODEX_COPILOT_SHARE_DIR"])
            runtime.mkdir(parents=True)
            (runtime / "user.txt").write_text("keep", encoding="utf-8")
            with self.assertRaises(installer.InstallError):
                installer.install()
            self.assertEqual((runtime / "user.txt").read_text(encoding="utf-8"), "keep")
            shutil.rmtree(runtime)
            installer.install()
            agent = Path(os.environ["CODEX_HOME"]) / "agents" / installer.AGENT_FILES[0]
            agent.write_text("user edited", encoding="utf-8")
            with self.assertRaises(installer.InstallError):
                installer.install()
            installer.uninstall()
            self.assertEqual(agent.read_text(encoding="utf-8"), "user edited")
            self.assertEqual(installer.load_manifest()["status"], "uninstall-residue")
            agent.unlink()
            installer.uninstall()
            self.assertIsNone(installer.load_manifest())

    def test_distribution_extra_files_and_generated_cache(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)):
            installer.install()
            runtime = Path(os.environ["CODEX_COPILOT_SHARE_DIR"])
            cache = runtime / "src" / "codex_copilot" / "__pycache__"
            cache.mkdir(exist_ok=True)
            (cache / "anything.pyc").write_bytes(b"runtime generated")
            self.assertFalse(installer.install()["changed"])
            (runtime / "user.txt").write_text("keep", encoding="utf-8")
            with self.assertRaises(installer.InstallError):
                installer.install()
            installer.uninstall()
            self.assertTrue((runtime / "user.txt").exists())

    def test_unknown_file_in_cache_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)):
            installer.install()
            note = Path(os.environ["CODEX_COPILOT_SHARE_DIR"]) / "src" / "__pycache__" / "user-note.txt"
            note.parent.mkdir(parents=True, exist_ok=True)
            note.write_text("user content", encoding="utf-8")
            with self.assertRaises(installer.InstallError):
                installer.install()
            installer.uninstall()
            self.assertEqual(note.read_text(encoding="utf-8"), "user content")

    @unittest.skipUnless(os.name == "posix", "v0.1.0 full installer supported POSIX only")
    def test_actual_v010_release_install_with_bytecode_upgrades(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)):
            original = Path(temp) / "old-source"
            with zipfile.ZipFile(Path(__file__).parent / "fixtures" / "release-0.1.0.zip") as archive:
                archive.extractall(original)
            config = Path(os.environ["CODEX_HOME"]) / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text('service_tier = "original"\n', encoding="utf-8")
            run = subprocess.run([sys.executable, str(original / "bin" / "codex-copilot"), "install", "--yes"], capture_output=True, text=True, encoding="utf-8", timeout=15)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(installer.load_manifest()["schema"], 1)
            cache = Path(os.environ["CODEX_COPILOT_SHARE_DIR"]) / "src" / "codex_copilot" / "__pycache__"
            self.assertTrue(any(cache.glob("*.pyc")))
            # A running old installation may regenerate bytecode; content stays intact.
            next(cache.glob("*.pyc")).write_bytes(b"regenerated cache")
            self.assertTrue(installer.install()["changed"])
            self.assertEqual(installer.load_manifest()["schema"], 2)
            installer.uninstall()
            self.assertEqual(tomllib.loads(config.read_text(encoding="utf-8"))["service_tier"], "original")

    def test_schema_one_distribution_fingerprint_migrates(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)):
            installer.install()
            manifest = installer.load_manifest()
            distribution = next(a for a in manifest["artifacts"] if a["kind"] == "distribution")
            cache = Path(distribution["target"]) / "src" / "codex_copilot" / "__pycache__"
            cache.mkdir(exist_ok=True)
            (cache / "generated.pyc").write_bytes(b"generated")
            import hashlib
            legacy = hashlib.sha256()
            root = Path(distribution["target"])
            for name in ("src", "skill", "agents", "bin", "VERSION"):
                path = root / name
                for child in [path] if path.is_file() else installer._fingerprint_files(path, include_cache=True):
                    legacy.update(str(child.relative_to(root)).encode())
                    legacy.update(child.read_bytes())
            distribution["fingerprint"] = legacy.hexdigest()
            distribution.pop("fingerprint_schema", None)
            manifest.update(schema=1, version="0.1.0")
            installer.manifest_path().write_text(json.dumps(manifest), encoding="utf-8")
            self.assertTrue(installer.install()["changed"])
            self.assertTrue(all(installer.artifact_matches(a) for a in installer.load_manifest()["artifacts"]))

    def test_verified_skill_adoption_backup_and_restore(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)):
            target = skills_home() / "codex-copilot"
            target.parent.mkdir(parents=True)
            shutil.copytree(repo_root() / "skill" / "codex-copilot", target)
            fingerprint = installer.artifact_fingerprint(target)
            preview = installer.install(dry_run=True)
            self.assertTrue(any("adopt" in action for action in preview["actions"]))
            installer.install(expected_plan_token=preview["plan_token"])
            artifact = next(a for a in installer.load_manifest()["artifacts"] if a["kind"] == "skill")
            self.assertTrue(Path(artifact["previous_backup"]).exists())
            installer.uninstall()
            self.assertEqual(installer.artifact_fingerprint(target), fingerprint)

    def test_adopted_skill_is_restored_when_registration_moves(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)):
            original = skills_home() / "codex-copilot"
            shutil.copytree(repo_root() / "skill" / "codex-copilot", original)
            fingerprint = installer.artifact_fingerprint(original)
            installer.install()
            with patch.dict(os.environ, {"CODEX_COPILOT_SKILLS_HOME": str(Path(temp) / "another-skills")}):
                with self.assertRaises(installer.InstallError):
                    installer.install()
            installer.uninstall()
            self.assertEqual(installer.artifact_fingerprint(original), fingerprint)

    def test_corrupt_manifest_is_diagnosable_and_cannot_uninstall(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)), patch("codex_copilot.cli.shutil.which", return_value=None), patch("codex_copilot.cli.get_quota", return_value=unknown_snapshot("test")):
            installer.manifest_path().parent.mkdir(parents=True)
            installer.manifest_path().write_text('{"schema":2}', encoding="utf-8")
            self.assertEqual(doctor()["installation_state"], "incomplete")
            with self.assertRaises(installer.InstallError):
                installer.uninstall(dry_run=True)
            for mode in ([], {}):
                installer.manifest_path().write_text(json.dumps({"schema": 2, "config_path": "test", "version": "0.1.1", "mode": mode, "artifacts": [], "config_changes": []}), encoding="utf-8")
                with self.assertRaises(installer.InstallError):
                    installer.load_manifest()

    def test_changing_codex_home_requires_uninstall(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)):
            installer.install()
            original = installer.manifest_path().read_bytes()
            with patch.dict(os.environ, {"CODEX_HOME": str(Path(temp) / "another-codex")}):
                with self.assertRaises(installer.InstallError):
                    installer.install()
            self.assertEqual(installer.manifest_path().read_bytes(), original)

    def test_unknown_skill_duplicate_and_preview_change(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)):
            target = skills_home() / "codex-copilot"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("unknown", encoding="utf-8")
            with self.assertRaises(installer.InstallError):
                installer.install()
            shutil.rmtree(target)
            preview = installer.install(dry_run=True)
            duplicate = Path(os.environ["CODEX_HOME"]) / "skills" / "codex-copilot"
            duplicate.mkdir(parents=True)
            (duplicate / "SKILL.md").write_text("unknown", encoding="utf-8")
            with self.assertRaises(installer.InstallError):
                installer.install(expected_plan_token=preview["plan_token"])
            self.assertFalse(Path(os.environ["CODEX_COPILOT_STATE_DIR"]).exists())

    def test_upgrade_rollback_restores_config_artifacts_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)):
            config = Path(os.environ["CODEX_HOME"]) / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text('# 中文 comment\nmodel = "custom"\n', encoding="utf-8")
            installer.install()
            manifest_bytes = installer.manifest_path().read_bytes()
            config_bytes = config.read_bytes()
            original = installer._atomic_write

            def fail_once(path, *args, **kwargs):
                if path == installer.manifest_path():
                    raise OSError("simulated locked manifest")
                return original(path, *args, **kwargs)

            with patch("codex_copilot.installer.VERSION", "0.1.2"), patch("codex_copilot.installer._atomic_write", side_effect=fail_once):
                with self.assertRaises(installer.InstallError):
                    installer.install()
            self.assertEqual(config.read_bytes(), config_bytes)
            self.assertEqual(installer.manifest_path().read_bytes(), manifest_bytes)
            self.assertTrue(all(installer.artifact_matches(a) for a in installer.load_manifest()["artifacts"]))
            config.write_text(config.read_text(encoding="utf-8").replace('service_tier = "standard"', 'service_tier = "custom"'), encoding="utf-8")
            installer.uninstall()
            self.assertEqual(tomllib.loads(config.read_text(encoding="utf-8"))["service_tier"], "custom")
            self.assertIn("中文", config.read_text(encoding="utf-8"))

    def test_doctor_installation_states_and_managed_config_drift(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)), patch(
            "codex_copilot.cli.shutil.which", return_value=None
        ), patch("codex_copilot.cli.get_quota", return_value=unknown_snapshot("unavailable")):
            target = skills_home() / "codex-copilot"
            shutil.copytree(repo_root() / "skill" / "codex-copilot", target)
            self.assertEqual(doctor()["installation_state"], "skill-only")
            installer.install()
            self.assertEqual(doctor()["installation_state"], "complete")
            config = Path(os.environ["CODEX_HOME"]) / "config.toml"
            config.write_text('service_tier = "custom"\n', encoding="utf-8")
            result = doctor()
            self.assertEqual(result["installation_state"], "incomplete")
            self.assertFalse(result["ok"])

    @unittest.skipUnless(os.name == "nt", "Windows launcher integration")
    def test_cmd_launcher_arguments_unicode_and_exit_code(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)):
            installer.install()
            launcher = Path(os.environ["CODEX_COPILOT_BIN_DIR"]) / "codex-copilot.cmd"
            # Replace only the sandbox Python entry with an argument echo sentinel.
            entry = launcher.with_suffix(".py")
            entry.write_text("import json,sys\nprint(json.dumps(sys.argv[1:],ensure_ascii=True))\nsys.exit(23)\n", encoding="utf-8")
            arguments = ["中文 argument", 'quoted "word"', "a&b", "100%", "!literal!", "plain"]
            command = '"' + str(launcher) + '" ' + subprocess.list2cmdline(arguments)
            # cmd metacharacters must be quoted by a caller, as with any .cmd CLI.
            command = command.replace(" a&b ", ' "a&b" ')
            result = subprocess.run(f'"{os.environ.get("COMSPEC", "cmd.exe")}" /d /s /c "{command}"', capture_output=True, text=True, encoding="utf-8", timeout=15)
            self.assertEqual(result.returncode, 23, result.stderr)
            self.assertEqual(json.loads(result.stdout), arguments)

    def test_alpha_version_is_supported(self):
        self.assertEqual(_version_tuple("codex-cli 0.159.0-alpha.12.1"), (0, 159, 0))

    @unittest.skipUnless(os.name == "nt", "Windows wait/exit behavior")
    def test_launch_propagates_exit_and_argument_boundaries(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)), patch(
            "codex_copilot.cli.get_quota", return_value=unknown_snapshot("unavailable")
        ), patch("codex_copilot.cli.codex_command", side_effect=lambda args: [sys.executable, "-c", "import sys;sys.exit(17)", *args]):
            args = argparse.Namespace(level="routine", profile=None, override_quota=False, dry_run=False, codex_args=["--", "中文 path"])
            self.assertEqual(_launch(args), 17)

    def test_missing_codex_is_an_actionable_error(self):
        with patch("codex_copilot.process.shutil.which", return_value=None):
            with self.assertRaises(FileNotFoundError):
                codex_command([])


@unittest.skipUnless(os.name == "nt", "Windows user PATH")
class UserPathTests(unittest.TestCase):
    def test_registry_restore_failure_still_rolls_back_files(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)):
            registry = {"present": True, "value": "", "type": 2}
            calls = []

            def fail_write(state):
                calls.append(dict(state))
                if len(calls) == 1:
                    registry.update(state)
                raise OSError("simulated registry error")

            with patch("codex_copilot.user_path.read", side_effect=lambda: dict(registry)), patch("codex_copilot.user_path.write", side_effect=fail_write):
                with self.assertRaisesRegex(installer.InstallError, "Rollback incomplete"):
                    installer.install(add_to_path=True)
            self.assertFalse(installer.manifest_path().exists())
            self.assertFalse(Path(os.environ["CODEX_COPILOT_SHARE_DIR"]).exists())
            self.assertFalse((Path(os.environ["CODEX_HOME"]) / "config.toml").exists())
            self.assertEqual(len(calls), 2)
    def test_changing_path_owned_bin_requires_uninstall(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)):
            registry = {"present": True, "value": "", "type": 2}
            with patch("codex_copilot.user_path.read", side_effect=lambda: dict(registry)), patch("codex_copilot.user_path.write", side_effect=lambda state: registry.update(state)):
                installer.install(add_to_path=True)
                after = dict(registry)
                with patch.dict(os.environ, {"CODEX_COPILOT_BIN_DIR": str(Path(temp) / "another-bin")}):
                    with self.assertRaises(installer.InstallError):
                        installer.install(add_to_path=True)
                self.assertEqual(registry, after)
                installer.uninstall()
                self.assertEqual(registry["value"], "")
    def test_path_is_opt_in_deduplicated_and_preserves_later_changes(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)):
            initial = {"present": True, "value": r"C:\existing", "type": 2}
            registry = dict(initial)

            def write(state):
                registry.clear()
                registry.update(state)

            with patch("codex_copilot.user_path.read", side_effect=lambda: dict(registry)), patch("codex_copilot.user_path.write", side_effect=write) as writer:
                installer.install(dry_run=True, add_to_path=True)
                writer.assert_not_called()
                installer.install()
                writer.assert_not_called()
                installer.install(add_to_path=True)
                self.assertEqual(writer.call_count, 1)
                installer.install(add_to_path=True)
                self.assertEqual(writer.call_count, 1)
                registry["value"] += r";C:\later"
                installer.uninstall()
                self.assertEqual(registry["value"], initial["value"] + r";C:\later")

    def test_existing_user_entry_is_not_owned(self):
        with tempfile.TemporaryDirectory() as temp:
            entry = str(Path(temp).resolve())
            existing = {"present": True, "value": entry.upper(), "type": 1}
            with patch("codex_copilot.user_path.read", return_value=existing):
                before, after, ownership = user_path.plan(Path(temp))
                self.assertFalse(ownership["added"])
                self.assertEqual(before, after)
                self.assertEqual(user_path.removal(ownership), (existing, existing))

    def test_path_change_invalidates_confirmation(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, environment(temp)):
            registry = {"present": True, "value": "", "type": 2}
            with patch("codex_copilot.user_path.read", side_effect=lambda: dict(registry)), patch("codex_copilot.user_path.write") as writer:
                preview = installer.install(dry_run=True, add_to_path=True)
                registry["value"] = r"C:\changed"
                with self.assertRaises(installer.InstallError):
                    installer.install(add_to_path=True, expected_plan_token=preview["plan_token"])
                writer.assert_not_called()
                self.assertFalse(Path(os.environ["CODEX_COPILOT_STATE_DIR"]).exists())


if __name__ == "__main__":
    unittest.main()
