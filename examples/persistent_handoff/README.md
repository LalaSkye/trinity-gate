# Lala × Trinity × Delta Persistent Handoff v0.1

A local **SQLite-backed synthetic workflow** for a source-bound handoff:

```text
Lala proposes → Trinity checks → Ricky's decision is recorded → Delta archives → STOP
```

This is **not an authenticated multi-agent system**, not a message sender and not a live authority service. The labels describe roles in a demonstration; callers can invoke all methods.

## Run

From the repository root with Python 3.11+:

```bash
python -m unittest discover -s tests -p 'test_persistent_handoff.py' -v
```

Import `Workflow` from `examples.persistent_handoff.workflow`. Supply a local SQLite path and use `propose`, `review`, `decide`, `archive`, `snapshot`, `verify_chain`, `close` in order. Restarting `Workflow(path)` resumes from durable SQLite state.

The test suite contains twelve cases for successful local transitions, restart, missing source, changed evidence, skipped review, duplicate job, replayed nonce, wrong destination, premature archive, altered event, unauthenticated identity and double decision.

## State and effect boundary

- `PROPOSED`: immutable source reference, version, source digest, object, destination and proposed text captured.
- `REVIEWED`: supplied review assertions and observed source digest match. **The tool does not read the original.**
- `HELD`: review failed; no decision transition.
- `DECIDED`: a caller-supplied decision with unique nonce, exact object, destination and digest recorded. **No proof that Ricky issued it.**
- `STOP`: local Delta-labelled receipt and terminal state. No external effect.

SQLite `BEGIN IMMEDIATE` transactions make each transition and receipt append atomic within this one local database. No network, remote agent, identity provider, signature verifier, external executor, or cloud persistence is involved.

## What is and is not proved

The `verify_chain` function checks local hash-link consistency, not independence or truth. An attacker with write access can regenerate a consistent chain. The source digest is supplied, not independently recomputed from source bytes. Nonces stop duplicate recorded decisions in this database, not distributed replay across services. An ALLOW value is only recorded, never executed.

**Review status:** Code and twelve tests published as review candidates. Do not treat tests as executed until a test-run receipt is produced. No CI success, security assurance, production readiness, autonomous action or novelty claim.

## Source basis

- [Delta function and custody map](https://app.notion.com/p/3c2276e494c48163a75febd30a4b2e01)
- [Lala/Trinity bounded adaptation loop](https://app.notion.com/p/37b276e494c48152a387c5cd9a9fc231)
- [Lala router/handoff inspection](https://app.notion.com/p/3fa276e494c481539f1fc94300752125)
- [Lala handoff protocol](https://app.notion.com/p/3c8276e494c48107a0dcd17efc0d36ed)

These were design sources, not proof of this implementation.

**STOP:** No real identities, private source documents, emails, deployments or external effects.
