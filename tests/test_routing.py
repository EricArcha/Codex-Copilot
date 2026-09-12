import unittest

from codex_copilot.routing import Profile, QuotaBand, TaskLevel, band_for_remaining, band_for_windows, route_for


class RoutingTests(unittest.TestCase):
    def test_band_boundaries(self):
        cases = [
            (None, QuotaBand.UNKNOWN),
            (60, QuotaBand.GREEN),
            (59.9, QuotaBand.YELLOW),
            (30, QuotaBand.YELLOW),
            (29.9, QuotaBand.RED),
            (10, QuotaBand.RED),
            (9.9, QuotaBand.CRITICAL),
        ]
        for remaining, expected in cases:
            with self.subTest(remaining=remaining):
                self.assertEqual(band_for_remaining(remaining), expected)

    def test_reached_overrides_percentage(self):
        self.assertEqual(band_for_remaining(90, reached=True), QuotaBand.CRITICAL)
        self.assertEqual(band_for_remaining(90, spend_control_reached=True), QuotaBand.CRITICAL)

    def test_standard_capacity_requires_both_windows(self):
        self.assertEqual(band_for_windows(86, 54), QuotaBand.GREEN)
        self.assertEqual(band_for_windows(49, 90), QuotaBand.YELLOW)
        self.assertEqual(band_for_windows(90, 19), QuotaBand.RED)

    def test_premium_uses_astra_only_for_l3_root_route(self):
        self.assertEqual(route_for(QuotaBand.GREEN, TaskLevel.L2, Profile.PREMIUM).root_model, "gpt-5.6-terra")
        self.assertEqual(route_for(QuotaBand.GREEN, TaskLevel.L3, Profile.PREMIUM).root_model, "gpt-6-astra")

    def test_route_matrix_invariants(self):
        for band in QuotaBand:
            for level in TaskLevel:
                route = route_for(band, level)
                with self.subTest(band=band, level=level):
                    self.assertLessEqual(route.max_subagents, 2)
                    self.assertFalse(route.allow_max_or_ultra)
                    if level is TaskLevel.L0:
                        self.assertEqual(route.max_subagents, 0)
                    if route.allow_sol:
                        self.assertEqual(level, TaskLevel.L3)

    def test_red_pauses_complex_and_critical(self):
        self.assertFalse(route_for(QuotaBand.RED, TaskLevel.L1).pause)
        self.assertTrue(route_for(QuotaBand.RED, TaskLevel.L2).pause)
        self.assertTrue(route_for(QuotaBand.RED, TaskLevel.L3).pause)

    def test_critical_always_pauses(self):
        for level in TaskLevel:
            self.assertTrue(route_for(QuotaBand.CRITICAL, level).pause)


if __name__ == "__main__":
    unittest.main()
