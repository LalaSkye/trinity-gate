"""Adversarial tests for synthetic persistent handoff state machine."""
import tempfile
import unittest
from pathlib import Path
from examples.persistent_handoff.workflow import Workflow, Hold

D = "a" * 64


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "handoff.db"
        self.w = Workflow(self.path)

    def tearDown(self):
        self.w.close()
        self.tmp.cleanup()

    def propose(self, job="j1"):
        self.w.propose(job_id=job, object_id="o1", destination="local:fixture",
                       source_ref="local:original", source_version="v1",
                       source_digest=D, text="Synthetic handoff")

    def review(self, job="j1", digest=D):
        return self.w.review(job, observed_source_digest=digest,
                             source_read=True, scope_ok=True, attribution_ok=True)

    def decide(self, job="j1", nonce="n1"):
        self.w.decide(job, decision="ALLOW", nonce=nonce, object_id="o1",
                      destination="local:fixture", observed_source_digest=D)

    def test_complete_and_zero_effect(self):
        self.propose()
        self.assertEqual(self.review(), "CHECKED")
        self.decide()
        self.w.archive("j1")
        s = self.w.snapshot("j1")
        self.assertEqual(s["job"]["stage"], "STOP")
        self.assertEqual(s["external_effects"], 0)
        self.assertTrue(self.w.verify_chain("j1"))

    def test_restart(self):
        self.propose()
        self.w.close()
        self.w = Workflow(self.path)
        self.assertEqual(self.review(), "CHECKED")
        self.decide()
        self.w.archive("j1")
        self.assertTrue(self.w.verify_chain("j1"))

    def test_missing_source(self):
        with self.assertRaises(Hold):
            self.w.propose(job_id="j1", object_id="o1", destination="local:fixture",
                           source_ref="", source_version="v1", source_digest=D, text="x")

    def test_changed_evidence_holds(self):
        self.propose()
        self.assertEqual(self.review(digest="b" * 64), "HOLD")
        with self.assertRaises(Hold):
            self.decide()

    def test_skip_review(self):
        self.propose()
        with self.assertRaises(Hold):
            self.decide()

    def test_replayed_job(self):
        self.propose()
        with self.assertRaises(Hold):
            self.propose()

    def test_replayed_nonce_across_jobs(self):
        self.propose()
        self.review()
        self.decide()
        self.propose("j2")
        self.review("j2")
        with self.assertRaises(Hold):
            self.decide("j2")

    def test_wrong_destination(self):
        self.propose()
        self.review()
        with self.assertRaises(Hold):
            self.w.decide("j1", decision="ALLOW", nonce="n1", object_id="o1",
                          destination="external:wrong", observed_source_digest=D)

    def test_cannot_archive_early(self):
        self.propose()
        with self.assertRaises(Hold):
            self.w.archive("j1")

    def test_tampered_event_detected(self):
        self.propose()
        self.w.db.execute("UPDATE events SET detail=? WHERE job_id='j1'", ('{"tampered":true}',))
        self.assertFalse(self.w.verify_chain("j1"))

    def test_no_identity_claim(self):
        self.propose()
        self.assertFalse(self.w.snapshot("j1")["identity_authenticated"])

    def test_double_decision_rejected(self):
        self.propose()
        self.review()
        self.decide()
        with self.assertRaises(Hold):
            self.decide(nonce="n2")


if __name__ == "__main__":
    unittest.main()
