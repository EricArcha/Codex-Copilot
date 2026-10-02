import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("check_release", Path(__file__).parents[1] / "scripts" / "check_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
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
