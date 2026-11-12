# Trinity × Lala: Handoff Rail v0.1

**Public, synthetic, non-executing example.** Separate from Trinity Gate's existing `email.send` demonstration and authority kernel.

```text
Lala proposes → Trinity reviews → Ricky decides → Delta records → STOP
```

The example preserves an exact source and version, speaker, author, recipient, destination, action, claim ceiling and stop condition. A Trinity review PASS never becomes action authority. A matching Ricky ALLOW can be **recorded in this synthetic state machine**, but cannot trigger any external effect.

## Run

From the repository root, with Python 3.11+:

```bash
python -m unittest discover -s tests -p 'test_trinity_lala_handoff.py' -v
```

To experiment interactively:

```python
from examples.trinity_lala_handoff.handoff import Handoff, verify

payload = dict(object_id="example-1", source="local:example", source_version="1",
    speaker="Ricky", author="Lala", recipient="Trinity", destination="local:demo",
    content="A synthetic proposal", requested_action="review",
    claim_ceiling="local illustration", stop_condition="no external action")
h = Handoff.begin(payload)
h.review(evidence_read=True, scope_ok=True, attribution_ok=True)
h.decide(decision="HOLD")
h.archive()
assert verify(h.export())
assert h.export()["effect_count"] == 0
```

## Evidence boundary

- Names are **role labels, not authenticated agents or human identities**.
- `evidence_read=True` is a supplied assertion, not source inspection.
- SHA-256 links detect accidental or unsophisticated edits to a fixed export; they are not signatures, immutable storage or independent witnesses.
- A malicious party can regenerate a completely consistent fabricated chain.
- `verify()` checks chain structure and limited stage consistency, not whether Ricky actually consented or the stated reasons were truthful.
- No Notion, Drive, email or external API is called.
- No production readiness, autonomy, safety certification or novelty is claimed.

## Source-informed design

- [Delta custody map](https://app.notion.com/p/3c2276e494c48163a75febd30a4b2e01)
- [Lala/Trinity bounded adaptation loop](https://app.notion.com/p/37b276e494c48152a387c5cd9a9fc231)
- [October router/handoff inspection](https://app.notion.com/p/3fa276e494c481539f1fc94300752125)
- [28 October Lala-to-Trinity handoff](https://docs.google.com/document/d/1LiT0fnoNPVcrcHe7KxbbIjwzAqMnjpl98oYZeyDL6WA/edit)

The underlying documents were read for design. The example contains no private message text or credentials.

## Status

Published as an additive example, **not installed as the active TrilogyOS handoff**. Existing Trinity Gate runtime, policy, decision signing and SQLite boundaries remain unchanged.
