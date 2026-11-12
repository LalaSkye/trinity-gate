"""Synthetic adversarial tests for authority race model."""
import unittest
from examples.authority_race_lab.race_lab import explore, schedules, report

class RaceLabTests(unittest.TestCase):
    def test_schedule_count(self):
        self.assertEqual(len(list(schedules())), 30)

    def test_unsafe_counterexample(self):
        s = ("A.check", "revoke", "A.commit", "B.check", "B.commit")
        self.assertEqual(explore(s).stale_effects, ("A",))

    def test_guard_blocks_same_schedule(self):
        s = ("A.check", "revoke", "A.commit", "B.check", "B.commit")
        self.assertEqual(explore(s, "effect_recheck").stale_effects, ())

    def test_all_guarded_schedules(self):
        self.assertTrue(all(not explore(s, "effect_recheck").stale_effects for s in schedules()))

    def test_valid_pre_revoke_effect(self):
        s = ("A.check", "A.commit", "B.check", "B.commit", "revoke")
        self.assertEqual(explore(s, "effect_recheck").accepted, ("A", "B"))

    def test_revoke_before_checks(self):
        s = ("revoke", "A.check", "A.commit", "B.check", "B.commit")
        self.assertEqual(explore(s).accepted, ())

    def test_bad_schedule_rejected(self):
        with self.assertRaises(ValueError):
            explore(("A.commit", "A.check", "B.check", "B.commit", "revoke"))

    def test_bad_mode_rejected(self):
        with self.assertRaises(ValueError):
            explore(("A.check", "A.commit", "B.check", "B.commit", "revoke"), "magic")

    def test_report(self):
        r = report()
        self.assertGreater(r["unsafe_stale_schedules"], 0)
        self.assertEqual(r["guarded_stale_schedules"], 0)

if __name__ == "__main__":
    unittest.main()
