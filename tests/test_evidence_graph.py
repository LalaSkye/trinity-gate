"""Adversarial checks for source independence, custody and claim boundaries."""
import copy
import unittest
from examples.evidence_graph.evidence_graph import audit


def fixture():
    return {'nodes': [
        {'id': 'c', 'kind': 'claim', 'status': 'REPORTED', 'source': 'local:claim'},
        {'id': 'r1', 'kind': 'original', 'status': 'VERIFIED', 'source': 'local:original1'},
        {'id': 'r2', 'kind': 'original', 'status': 'VERIFIED', 'source': 'local:original2'},
        {'id': 's', 'kind': 'summary', 'status': 'REPORTED', 'source': 'local:summary'},
    ], 'edges': [
        {'from': 'c', 'to': 'r1', 'relation': 'supports'},
        {'from': 'c', 'to': 'r2', 'relation': 'supports'},
    ], 'claims': [{'claim': 'c', 'min_independent_roots': 2}]}


class GraphTests(unittest.TestCase):
    def test_two_independent_roots(self):
        self.assertEqual(audit(fixture())['results'][0]['verdict'], 'CHECKED')

    def test_two_summaries_one_original(self):
        d = fixture()
        d['nodes'].append({'id': 's2', 'kind': 'report', 'status': 'REPORTED', 'source': 'local:report'})
        d['edges'] = [{'from': 'c', 'to': 's', 'relation': 'supports'},
                      {'from': 'c', 'to': 's2', 'relation': 'supports'},
                      {'from': 's', 'to': 'r1', 'relation': 'derived_from'},
                      {'from': 's2', 'to': 'r1', 'relation': 'derived_from'}]
        r = audit(d)['results'][0]
        self.assertEqual(r['root_ids'], ['r1'])
        self.assertIn('INSUFFICIENT_INDEPENDENT_ROOTS', r['reasons'])

    def test_unbound_summary(self):
        d = fixture()
        d['edges'] = [{'from': 'c', 'to': 's', 'relation': 'supports'}]
        self.assertIn('UNBOUND_LINEAGE', audit(d)['results'][0]['reasons'])

    def test_superseded_root(self):
        d = fixture()
        d['edges'].append({'from': 'r2', 'to': 'r1', 'relation': 'supersedes'})
        self.assertIn('SUPERSEDED_ROOT', audit(d)['results'][0]['reasons'])

    def test_conflicting_root(self):
        d = fixture()
        d['edges'].append({'from': 'r2', 'to': 'r1', 'relation': 'contradicts'})
        self.assertIn('CONTRADICTED_ROOT', audit(d)['results'][0]['reasons'])

    def test_unverified_root(self):
        d = fixture()
        d['nodes'][1]['status'] = 'REPORTED'
        self.assertIn('ROOT_NOT_VERIFIED', audit(d)['results'][0]['reasons'])

    def test_cycle(self):
        d = fixture()
        d['edges'].extend([{'from': 's', 'to': 'r1', 'relation': 'derived_from'},
                           {'from': 'r1', 'to': 's', 'relation': 'derived_from'}])
        with self.assertRaises(ValueError):
            audit(d)

    def test_duplicate_id(self):
        d = fixture()
        d['nodes'].append(copy.deepcopy(d['nodes'][0]))
        with self.assertRaises(ValueError):
            audit(d)

    def test_no_authority_claim(self):
        r = audit(fixture())
        self.assertFalse(r['authority_verified'])
        self.assertEqual(r['external_effects'], 0)

    def test_missing_support(self):
        d = fixture()
        d['edges'] = []
        self.assertIn('NO_SUPPORT', audit(d)['results'][0]['reasons'])


if __name__ == '__main__':
    unittest.main()
