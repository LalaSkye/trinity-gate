# Trinity Gate v0.2

Trinity Gate is a bounded pre-action control for agentic workflows.

It checks one proposed action against an exact, signed `DecisionRecord` before
the action can reach consequence, then records the verdict in a hash-chained
receipt log.

```text
request -> policy check -> HOLD / DENY / ALLOW -> simulated effect -> receipt
```

## Current proof surface

The first vertical slice protects one demonstration action: `email.send`.
The "send" writes to a local SQLite outbox. It cannot contact an email provider
or send a real message.

The product layer imports
[`commit-gate-core` v0.1.1](https://github.com/LalaSkye/commit-gate-core/releases/tag/v0.1.1)
rather than copying or altering its gate logic.

## What is implemented

- Python `check_action()` API
- small JSON-over-HTTP API
- machine-readable JSON policy
- exact binding of actor, action, object, environment, target and payload
- scoped, expiring, one-use `DecisionRecord`
- `ALLOW`, `HOLD` and `DENY` product verdicts
- HMAC verification for the local demonstration
- atomic SQLite nonce, outbox and receipt transaction
- hash-chained receipts with a verification command
- JSONL receipt export for inspection
- Docker entry point
- bounded HOLD -> human decision -> ALLOW demonstration

## Run locally

Requires Python 3.11 or later and the released core dependency.

```bash
python -m pip install -e .
export TRINITY_GATE_DEMO_SECRET='replace-with-a-local-demo-secret'
python scripts/run_demo.py
```

Expected shape:

```text
first verdict:  HOLD
second verdict: ALLOW
outbox rows:    1
receipt chain:  valid
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

Run the local HTTP service:

```bash
export TRINITY_GATE_DEMO_SECRET='replace-with-a-local-demo-secret'
python -m trinity_gate.http_api
```

Then POST JSON to `http://127.0.0.1:8080/v1/check` with a `request` object and,
when available, a `decision_record` object.

## Docker

```bash
docker build -t trinity-gate:v0.2.0 .
docker run --rm -p 8080:8080 \
  -e TRINITY_GATE_DEMO_SECRET='replace-with-a-local-demo-secret' \
  trinity-gate:v0.2.0
```

## Claim boundary

This is an alpha vertical slice and a local proof object. It does not claim:

- production readiness
- real email delivery
- non-bypassability outside the demonstrated path
- independent security review
- compliance, certification or audit equivalence
- secure enterprise key management
- a completed TrinityOS product

HMAC signing is present only to make the local approval path runnable. A
production deployment would need an external identity and key-management
boundary, authenticated approvers, durable operational controls and an
independent threat review.

See [Product Boundary](docs/PRODUCT_BOUNDARY.md).
See [Provenance](docs/PROVENANCE.md).
