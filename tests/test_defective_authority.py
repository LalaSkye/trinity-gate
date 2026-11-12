import unittest
from examples.defective_authority.authority import Gate, sign

SECRET = b'local-demo-key-not-production'
RECORD = dict(issuer='issuer-A', object_id='object-1', destination='local:outbox', nonce='nonce-1', expires_at=100)
ENT = dict(issuer='issuer-A', object_id='object-1', destination='local:outbox', active=True, revoked_at=None)

class Tests(unittest.TestCase):
    def setUp(self):
        self.g = Gate(SECRET)
    def run_case(self, record=None, entitlement=ENT, now=10, signature=None):
        record = record or RECORD
        return self.g.execute(record, sign(SECRET, record) if signature is None else signature, entitlement=entitlement, now=now)
    def test_valid_positive(self):
        self.assertEqual(self.run_case().verdict, 'ALLOW')
        self.assertEqual(self.g.count(), 1)
    def test_valid_signature_wrong_issuer_entitlement(self):
        self.assertEqual(self.run_case(entitlement={**ENT, 'issuer':'issuer-B'}).reason, 'ISSUER_NOT_ENTITLED_FOR_SCOPE')
        self.assertEqual(self.g.count(), 0)
    def test_wrong_destination(self):
        self.assertEqual(self.run_case(entitlement={**ENT, 'destination':'local:other'}).reason, 'ISSUER_NOT_ENTITLED_FOR_SCOPE')
    def test_revoked(self):
        self.assertEqual(self.run_case(entitlement={**ENT, 'revoked_at':5}).reason, 'ISSUER_AUTHORITY_REVOKED')
    def test_replay(self):
        self.run_case()
        self.assertEqual(self.run_case().reason, 'REPLAYED_DECISION')
        self.assertEqual(self.g.count(), 1)
    def test_missing_origin(self):
        self.assertEqual(self.run_case(entitlement=None).reason, 'ORIGIN_AUTHORITY_UNPROVEN')
    def test_invalid_signature(self):
        self.assertEqual(self.run_case(signature='00').reason, 'INVALID_SIGNATURE')
    def test_expired(self):
        self.assertEqual(self.run_case(now=100).reason, 'EXPIRED_RECORD')
    def test_reason_not_revocation_for_wrong_scope(self):
        result = self.run_case(entitlement={**ENT, 'object_id':'object-2'})
        self.assertEqual(result.reason, 'ISSUER_NOT_ENTITLED_FOR_SCOPE')
        self.assertNotEqual(result.reason, 'ISSUER_AUTHORITY_REVOKED')
    def test_bad_record(self):
        self.assertEqual(self.g.execute({'nonce':'x'}, 'x', entitlement=ENT, now=1).reason, 'MALFORMED_RECORD')

if __name__ == '__main__': unittest.main()
