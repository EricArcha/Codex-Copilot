import tomllib
import unittest

from codex_copilot.config_edit import apply_updates, restore_updates


class ConfigEditTests(unittest.TestCase):
    def test_adds_sections_and_preserves_unrelated_comments(self):
        original = '# keep me\nmodel = "old"\n\n[mcp_servers.demo]\nenabled = true\n'
        updated, changes = apply_updates(
            original,
            {
                "model": "gpt-5.6-terra",
                "agents.enabled": True,
                "agents.max_concurrent_threads_per_session": 3,
            },
        )
        parsed = tomllib.loads(updated)
        self.assertIn("# keep me", updated)
        self.assertTrue(parsed["mcp_servers"]["demo"]["enabled"])
        self.assertEqual(parsed["model"], "gpt-5.6-terra")
        self.assertEqual(parsed["agents"]["max_concurrent_threads_per_session"], 3)
        restored, warnings = restore_updates(updated, [change.__dict__ for change in changes])
        self.assertEqual(tomllib.loads(restored)["model"], "old")
        self.assertEqual(tomllib.loads(restored).get("agents"), {})
        self.assertEqual(warnings, [])

    def test_uninstall_preserves_later_user_edit(self):
        updated, changes = apply_updates('model = "old"\n', {"model": "installed"})
        user_text = updated.replace('model = "installed"', 'model = "mine"')
        restored, warnings = restore_updates(user_text, [change.__dict__ for change in changes])
        self.assertEqual(tomllib.loads(restored)["model"], "mine")
        self.assertEqual(len(warnings), 1)

    def test_updates_root_dotted_key_without_duplicate_table(self):
        original = 'agents.enabled = false\n'
        updated, _ = apply_updates(
            original,
            {"agents.enabled": True, "agents.max_concurrent_threads_per_session": 3},
        )
        self.assertTrue(tomllib.loads(updated)["agents"]["enabled"])
        self.assertEqual(tomllib.loads(updated)["agents"]["max_concurrent_threads_per_session"], 3)
        self.assertNotIn("[agents]", updated)

    def test_array_tables_end_managed_sections_and_root_scope(self):
        original = ('# keep\n[agents]\nmax_concurrent_threads_per_session = 3\n'
                    '[[skills.config]]\npath = "one"\nenabled = true\n'
                    '[[skills.config]]\npath = "two"\nenabled = false\n')
        updates = {"agents.default_subagent_model": "gpt-6-luna",
                   "agents.default_subagent_reasoning_effort": "low", "model": "test"}
        updated, changes = apply_updates(original, updates)
        parsed = tomllib.loads(updated)
        self.assertEqual(parsed["agents"]["default_subagent_model"], "gpt-6-luna")
        self.assertEqual(parsed["agents"]["default_subagent_reasoning_effort"], "low")
        self.assertEqual(parsed["model"], "test")
        self.assertEqual(parsed["skills"], tomllib.loads(original)["skills"])
        again, _ = apply_updates(updated, updates)
        self.assertEqual(again, updated)
        restored, warnings = restore_updates(updated, [c.__dict__ for c in changes])
        self.assertEqual(tomllib.loads(restored), tomllib.loads(original))
        self.assertFalse(warnings)

    def test_root_dotted_keys_are_not_written_into_array_tables(self):
        original = '[[skills.config]]\npath = "one"\n'
        updated, _ = apply_updates(original, {"agents.enabled": True})
        self.assertTrue(tomllib.loads(updated)["agents"]["enabled"])
        self.assertEqual(tomllib.loads(updated)["skills"], tomllib.loads(original)["skills"])

    def test_header_looking_multiline_string_is_preserved(self):
        for quote in ('"""', "'" * 3):
            original = ('[agents]\nnotes = ' + quote + '\n[[skills.config]]\n'
                        '[agents]\nenabled = false\n' + quote + '\nenabled = true\n'
                        '[[skills.config]]\npath = "one"\n')
            updated, changes = apply_updates(original, {"agents.enabled": True,
                                                       "agents.model": "test"})
            before, after = tomllib.loads(original), tomllib.loads(updated)
            self.assertEqual(before["agents"]["notes"], after["agents"]["notes"])
            self.assertEqual(before["skills"], after["skills"])
            self.assertEqual(after["agents"]["model"], "test")
            restored, warnings = restore_updates(updated, [c.__dict__ for c in changes])
            self.assertEqual(tomllib.loads(restored), before)
            self.assertFalse(warnings)

    def test_invalid_toml_is_rejected(self):
        with self.assertRaises(tomllib.TOMLDecodeError):
            apply_updates("[broken\n", {"model": "x"})


if __name__ == "__main__":
    unittest.main()
