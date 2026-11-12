"""Positive and adversarial cases for the separate origin registry model."""
import unittest
from examples.defective_authority.origin_registry import OriginGate, sign

KEY = b"synthetic-demo-key"
RECORD = dict(issuer="I", object_id="O", destination="local:D", nonce="N", expires_at=100)

class OriginRegistryTests(unittest.TestCase):
    def setUp(self):
        self.g = OriginGate(KEY)
    def run_record(self, record=None, signature=None, now=10):
        record = RECORD if record is None else record
        return self.g.execute(record, sign(KEY, record) if signature is None else signature, now)
    def seed(self):
        self.g.seed_entitlement(issuer="I", object_id="O", destination="local:D")
    def test_positive(self):
        self.seed()
        self.assertEqual(self.run_record(), "ALLOW:SIMULATED_EFFECT")
        self.assertEqual(self.g.effect_count(), 1)
    def test_signed_without_origin(self):
        self.assertEqual(self.run_record(), "HOLD:ORIGIN_NOT_ESTABLISHED")
        self.assertEqual(self.g.effect_count(), 0)
    def test_wrong_scope(self):
        self.seed()
        r = {**RECORD, "destination":"local:OTHER"}
        self.assertEqual(self.run_record(r), "HOLD:ORIGIN_NOT_ESTABLISHED")
    def test_revocation(self):
        self.seed()
        self.g.revoke(issuer="I", object_id="O", destination="local:D", at=5)
        self.assertEqual(self.run_record(), "DENY:REVOKED")
    def test_replay(self):
        self.seed()
        self.run_record()
        self.assertEqual(self.run_record(), "DENY:REPLAY")
        self.assertEqual(self.g.effect_count(), 1)
    def test_signature(self):
        self.seed()
        self.assertEqual(self.run_record(signature="invalid"), "DENY:INVALID_SIGNATURE")
    def test_expiry(self):
        self.seed()
        self.assertEqual(self.run_record(now=100), "DENY:EXPIRED")
    def test_reason_fidelity(self):
        self.assertNotEqual(self.run_record(), "DENY:REVOKED")
    def test_no_effect_on_hold(self):
        self.run_record()
        self.assertEqual(self.g.effect_count(), 0)
    def test_invalid_input(self):
        self.assertEqual(self.g.execute({"nonce":"N"}, "x", 10), "DENY:MALFORMED_RECORD")

if __name__ == "__main__":
    unittest.main()
