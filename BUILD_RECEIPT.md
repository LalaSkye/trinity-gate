# Trinity Gate v0.2.0 Build Receipt

**Built:** 2026-08-05T01:40:41Z  
**State:** LOCAL / NOT PUBLISHED / NOT DEPLOYED

## Object

Separate `trinity-gate` product repository importing `commit-gate-core` v0.1.1.

## Verified

- Python source compilation: PASS
- Standard-library unit and integration tests: **14 passed, 0 failed**
- Live local HTTP `POST /v1/check`: PASS (`HOLD` without authority)
- Demonstration route: `HOLD -> signed DecisionRecord -> ALLOW`
- Simulated email outbox rows after exact approval: **1**
- Replay refusal: PASS
- Expiry refusal: PASS
- Target and payload drift refusal: PASS
- Invalid signature refusal: PASS
- Audit failure rolls back the staged effect: PASS
- Receipt alteration detection: PASS
- Receipt export preserves exact target and chain hash: PASS
- Wheel build: PASS
- Installed wheel loads bundled default policy: PASS

## Package receipt

- Wheel: `trinity_gate-0.2.0-py3-none-any.whl`
- SHA-256: `d3833411cffdebdc8902931ec4d4d9cc02528e1cd3ce8f269732509d4c579346`

## Not verified

- Docker image execution: Docker is unavailable in this workspace.
- Network installation of the tagged core dependency.
- Real email delivery or any external consequential action.
- Production identity, secrets or key-management integration.
- Security penetration testing, performance, certification or compliance.

## Negative-space receipt

No remote repository was created. Nothing was pushed, published, deployed,
emailed or connected to a production system. No source inspection pack was
bundled into the product.

STOP - local vertical slice built and verified; publication requires fresh
authority and a named GitHub destination/visibility.

