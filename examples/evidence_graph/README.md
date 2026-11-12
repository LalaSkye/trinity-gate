# Trinity Evidence Graph v0.1

A **local, non-executing evidence-lineage auditor** built from the failure patterns in TrinityOS's Delta archive. It is an additive example, not a replacement for the existing gate, a truth engine or a certification system.

## What it detects

- Two apparently independent reports derived from the **same original** (one root, not two).
- A claim supported by an unbound summary with no original.
- Superseded or contradicted source roots.
- Source roots whose verification state is only reported.
- Cycles, duplicate node IDs and missing supporting evidence.

The output is `CHECKED` (declared graph structure satisfies the stated checks) or `HOLD`. **CHECKED is not PASS, ALLOW, independent verification or permission.**

## Run

From the repository root, with Python 3.11+:

```bash
python examples/evidence_graph/evidence_graph.py examples/evidence_graph/sample.json
python -m unittest discover -s tests -p 'test_evidence_graph.py' -v
```

Exit status 0: all requested claims CHECKED. Exit status 1: at least one HOLD. Exit status 2: invalid input. The tool writes nothing to disk.

## Input schema

Three top-level arrays: `nodes`, `edges`, `claims`.

- Node: `{ "id": "...", "kind": "original|excerpt|summary|report|claim", "status": "VERIFIED|REPORTED|UNRESOLVED", "source": "..." }`
- Edge: `{ "from": "...", "to": "...", "relation": "supports|derived_from|supersedes|contradicts" }`
- Claim request: `{ "claim": "...", "min_independent_roots": 2 }`

Edges point **from a claim to its evidence**, and **from a derived item to its predecessor**. `supersedes` points from the newer record to the older one.

## Critical limits

1. **No source bytes are fetched or checked.** A node marked `VERIFIED` is an input assertion. The auditor does not establish that verification occurred.
2. Independence is approximated by distinct original node IDs. The same original can be entered twice under different IDs; this tool cannot discover that. Real independence needs source identities, custody, provenance and external verification.
3. A complete fabricated graph can yield CHECKED. The output hash fingerprints the supplied JSON; it is not a digital signature or independent witness.
4. A contradiction edge is supplied by the caller; the tool does not determine semantic contradictions.
5. No external actions, private data, network calls, authority decisions or production claims.

## Why this exists

Delta's [archive crosswalk](https://app.notion.com/p/47994fb5fb364d98906b5642fee44b81) documents handoff hardening, inherited PASS, supersession confusion and receipt/claim-ceiling mismatches. The [failure topology](https://app.notion.com/p/aa6bee7ffe6b41319b2a7e3a1da26b4f) warns against certainty theatre. This tool makes **one bounded structural check** executable without promoting the archival notes into runtime proof.

Ten synthetic unit tests were run locally on 12 November 2026 before publication. Repository-wide CI and independent review are not claimed.

**STOP:** Synthetic demonstration only. No new novelty or production safety claim.
