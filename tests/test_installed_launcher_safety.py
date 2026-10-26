"""F-01 planner acceptance: roll back a partial installed setting change."""

import os
import subprocess
import sys
import unittest

from tests import test_installed_launcher as launcher_tests


class InstalledLauncherRollbackTests(unittest.TestCase):
    def test_manifest_failure_restores_policy_and_manifest(self):
        fixture = launcher_tests.InstalledLauncherSettingTests()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        fixture.install_from_source("off")
        before_policy = fixture.policy.read_bytes()
        before_manifest = fixture.manifest.read_bytes()
        child = dict(os.environ)
        child.pop("PYTHONPATH", None)
        # Load the runtime named by the real launcher, inject only the final
        # manifest write failure, then execute that launcher with normal argv.
        code = r'''
import json, runpy, sys
from pathlib import Path
from unittest.mock import patch
launcher, manifest, policy = map(Path, sys.argv[1:])
pointer = launcher.with_name("codex-copilot.runtime.json")
sys.path.insert(0, str(Path(json.loads(pointer.read_text())["root"]) / "src"))
from codex_copilot import installer
original = installer._atomic_write
def fail_manifest(target, content, mode=None):
    if Path(target) == manifest:
        assert "  allow_implicit_invocation: true" in policy.read_text(), "setting was not written"
        raise OSError("injected manifest failure after setting write")
    return original(target, content, mode)
sys.argv = [str(launcher), "install", "--implicit-invocation", "on", "--yes"]
with patch.object(installer, "_atomic_write", side_effect=fail_manifest):
    runpy.run_path(str(launcher), run_name="__main__")
'''
        result = subprocess.run(
            [sys.executable, "-c", code, str(fixture.launcher),
             str(fixture.manifest), str(fixture.policy)],
            env=child, cwd=fixture.temp.name, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("injected manifest failure after setting write", result.stderr)
        self.assertEqual(fixture.policy.read_bytes(), before_policy)
        self.assertEqual(fixture.manifest.read_bytes(), before_manifest)


if __name__ == "__main__":
    unittest.main()
