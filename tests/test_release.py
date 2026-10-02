import importlib.util
from pathlib import Path
import tempfile
import subprocess
from unittest.mock import patch
import unittest

spec = importlib.util.spec_from_file_location("check_release", Path(__file__).parents[1] / "scripts" / "check_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_tag_source_fence_rejects_private_product_additions(self):
        for output in ("?? src/private-notes.txt\n", " M skill/codex-copilot/SKILL.md\n"):
            with self.subTest(output=output), patch.object(release.subprocess, "run", side_effect=[
                subprocess.CompletedProcess([], 0, output, ""), subprocess.CompletedProcess([], 0, "", "")
            ]):
                with self.assertRaisesRegex(ValueError, "uncommitted or untracked") as caught:
                    release.check_product_tree(Path("."))
                self.assertNotIn("private-notes", str(caught.exception))
        with patch.object(release.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")):
            release.check_product_tree(Path("."))

    def test_tag_source_fence_rejects_ignored_credentials(self):
        clean = subprocess.CompletedProcess([], 0, "", "")
        for content, rejected in [("src/.env\0", True), ("src/private.key\0", True),
                                  ("src/__pycache__/quota.pyc\0", False)]:
            with self.subTest(rejected=rejected), patch.object(release.subprocess, "run", side_effect=[
                clean, subprocess.CompletedProcess([], 0, content, "")
            ]):
                if rejected:
                    with self.assertRaisesRegex(ValueError, "ignored non-runtime"):
                        release.check_product_tree(Path("."))
                else:
                    release.check_product_tree(Path("."))

    def test_real_git_ignored_product_secret_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "--quiet"], cwd=root, check=True, capture_output=True)
            (root / ".gitignore").write_text(".env\n*.key\n*.pyc\n")
            (root / "src").mkdir()
            (root / "src" / "generated.pyc").write_bytes(b"bytecode")
            release.check_product_tree(root)
            for name in (".env", "private.key"):
                path = root / "src" / name
                path.write_text("private-token")
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, "ignored non-runtime") as caught:
                    release.check_product_tree(root)
                self.assertNotIn(name, str(caught.exception))
                path.unlink()

    def test_current_metadata_and_tag_match(self):
        from codex_copilot import VERSION
        self.assertEqual(release.validate(Path(__file__).parents[1], f"v{VERSION}"), VERSION)

    def test_rejects_mismatch_missing_notes_and_invalid_tag(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "VERSION").write_text("1.0.0\n")
            (root / "pyproject.toml").write_text('[project]\nversion = "1.0.1"\n')
            (root / "CHANGELOG.md").write_text("## [1.0.0] - 2026-10-02\n")
            with self.assertRaisesRegex(ValueError, "pyproject"):
                release.validate(root)
            (root / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\n')
            with self.assertRaisesRegex(ValueError, "tag"):
                release.validate(root, "v0.1.1")
            (root / "CHANGELOG.md").write_text("no entry")
            with self.assertRaisesRegex(ValueError, "CHANGELOG"):
                release.validate(root)
