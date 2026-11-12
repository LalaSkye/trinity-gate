"""Offline evidence lineage auditor; not a truth or authority oracle."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

KINDS = {'original', 'excerpt', 'summary', 'report', 'claim'}
RELATIONS = {'supports', 'derived_from', 'supersedes', 'contradicts'}


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def audit(document):
    if not isinstance(document, dict) or set(document) != {'nodes', 'edges', 'claims'}:
        raise ValueError('expected nodes, edges, claims')
    nodes, edges, requests = document['nodes'], document['edges'], document['claims']
    if not isinstance(nodes, list) or not isinstance(edges, list) or not isinstance(requests, list):
        raise ValueError('nodes, edges and claims must be lists')
    index = {}
    for node in nodes:
        if not isinstance(node, dict) or set(node) != {'id', 'kind', 'status', 'source'}:
            raise ValueError('invalid node')
        if not isinstance(node['id'], str) or not node['id'] or node['id'] in index:
            raise ValueError('duplicate/invalid node id')
        if node['kind'] not in KINDS or node['status'] not in {'VERIFIED', 'REPORTED', 'UNRESOLVED'}:
            raise ValueError('invalid node kind/status')
        if not isinstance(node['source'], str) or not node['source']:
            raise ValueError('source required')
        index[node['id']] = node
    outgoing = defaultdict(list)
    superseded = set()
    conflicts = set()
    for edge in edges:
        if not isinstance(edge, dict) or set(edge) != {'from', 'to', 'relation'}:
            raise ValueError('invalid edge')
        a, b, rel = edge['from'], edge['to'], edge['relation']
        if a not in index or b not in index or rel not in RELATIONS or a == b:
            raise ValueError('invalid edge endpoints/relation')
        outgoing[a].append((rel, b))
        if rel == 'supersedes':
            superseded.add(b)
        if rel == 'contradicts':
            conflicts.update((a, b))
    visited, active = set(), set()
    def visit(n):
        if n in active:
            raise ValueError('cycle in evidence lineage')
        if n in visited:
            return
        active.add(n)
        for rel, target in outgoing[n]:
            if rel in {'supports', 'derived_from'}:
                visit(target)
        active.remove(n)
        visited.add(n)
    for n in index:
        visit(n)

    def roots(node_id):
        node = index[node_id]
        if node['kind'] == 'original':
            return {node_id}, set()
        lineage = [target for rel, target in outgoing[node_id] if rel == 'derived_from']
        if not lineage:
            return set(), {node_id}
        found, gaps = set(), set()
        for target in lineage:
            a, b = roots(target)
            found.update(a)
            gaps.update(b)
        return found, gaps

    results = []
    for req in requests:
        if not isinstance(req, dict) or set(req) != {'claim', 'min_independent_roots'}:
            raise ValueError('invalid claim request')
        name, minimum = req['claim'], req['min_independent_roots']
        if name not in index or index[name]['kind'] != 'claim' or type(minimum) is not int or minimum < 1:
            raise ValueError('invalid claim/minimum')
        reasons, roots_found, gaps = set(), set(), set()
        support = [b for rel, b in outgoing[name] if rel == 'supports']
        if not support:
            reasons.add('NO_SUPPORT')
        for evidence in support:
            a, b = roots(evidence)
            roots_found.update(a)
            gaps.update(b)
            if evidence in superseded:
                reasons.add('SUPERSEDED_SUPPORT')
            if evidence in conflicts:
                reasons.add('CONTRADICTED_SUPPORT')
        for root in roots_found:
            if index[root]['status'] != 'VERIFIED':
                reasons.add('ROOT_NOT_VERIFIED')
            if root in superseded:
                reasons.add('SUPERSEDED_ROOT')
            if root in conflicts:
                reasons.add('CONTRADICTED_ROOT')
        if gaps:
            reasons.add('UNBOUND_LINEAGE')
        if len(roots_found) < minimum:
            reasons.add('INSUFFICIENT_INDEPENDENT_ROOTS')
        results.append({'claim': name, 'verdict': 'CHECKED' if not reasons else 'HOLD',
                        'root_ids': sorted(roots_found), 'unbound_ids': sorted(gaps),
                        'reasons': sorted(reasons)})
    return {'schema': 'trinity-evidence-graph/0.1', 'input_sha256': hashlib.sha256(canonical(document).encode()).hexdigest(),
            'results': results, 'authority_verified': False, 'external_effects': 0}


def main():
    parser = argparse.ArgumentParser(description='Offline source-lineage audit')
    parser.add_argument('input', type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding='utf-8'))
        result = audit(data)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        print(json.dumps({'error': str(exc), 'verdict': 'HOLD'}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(r['verdict'] == 'CHECKED' for r in result['results']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
