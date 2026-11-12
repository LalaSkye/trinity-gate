"""Adversarial controls for the standalone handoff demonstration."""
import unittest
from examples.trinity_lala_handoff.handoff import Handoff, verify

BASE = dict(object_id="case-001", source="local:fixture", source_version="1",
            speaker="Ricky", author="Lala", recipient="Trinity",
            destination="local:demo", content="Example only", requested_action="review",
            claim_ceiling="synthetic only", stop_condition="no external action")


class HandoffTests(unittest.TestCase):
    def begin(self):
        return Handoff.begin(BASE)

    def test_complete_allow_no_effect(self):
        h = self.begin()
        self.assertEqual(h.review(evidence_read=True, scope_ok=True, attribution_ok=True), "PASS")
        h.decide(decision="ALLOW", object_id="case-001", destination="local:demo")
        h.archive()
        self.assertTrue(verify(h.export()))
        self.assertEqual(h.export()["effect_count"], 0)

    def test_hold(self):
        h = self.begin()
        h.review(evidence_read=False, scope_ok=True, attribution_ok=True)
        h.decide(decision="HOLD")
        h.archive()
        self.assertTrue(verify(h.export()))

    def test_missing_source(self):
        with self.assertRaises(ValueError):
            Handoff.begin({**BASE, "source": ""})

    def test_role_substitution(self):
        h = self.begin()
        with self.assertRaises(ValueError):
            h.review(evidence_read=True, scope_ok=True, attribution_ok=True, reviewer="Delta")

    def test_skip_review(self):
        with self.assertRaises(ValueError):
            self.begin().decide(decision="ALLOW", object_id="case-001", destination="local:demo")

    def test_allow_after_hold(self):
        h = self.begin()
        h.review(evidence_read=False, scope_ok=True, attribution_ok=True)
        with self.assertRaises(ValueError):
            h.decide(decision="ALLOW", object_id="case-001", destination="local:demo")

    def test_wrong_destination(self):
        h = self.begin()
        h.review(evidence_read=True, scope_ok=True, attribution_ok=True)
        with self.assertRaises(ValueError):
            h.decide(decision="ALLOW", object_id="case-001", destination="external:other")

    def test_tampered_payload(self):
        h = self.begin()
        h.review(evidence_read=True, scope_ok=True, attribution_ok=True)
        record = h.export()
        record["payload"]["content"] = "altered"
        self.assertFalse(verify(record))

    def test_tampered_verdict(self):
        h = self.begin()
        h.review(evidence_read=False, scope_ok=True, attribution_ok=True)
        record = h.export()
        record["events"][1]["verdict"] = "PASS"
        self.assertFalse(verify(record))

    def test_no_execution_on_replay(self):
        h = self.begin()
        h.review(evidence_read=True, scope_ok=True, attribution_ok=True)
        h.decide(decision="ALLOW", object_id="case-001", destination="local:demo")
        h.archive()
        self.assertEqual(h.export()["effect_count"], 0)
        self.assertTrue(verify(h.export()))

    def test_reject_extra_stage(self):
        h = self.begin()
        h.review(evidence_read=True, scope_ok=True, attribution_ok=True)
        record = h.export()
        record["events"].append(record["events"][-1].copy())
        self.assertFalse(verify(record))


if __name__ == "__main__":
    unittest.main()
