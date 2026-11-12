# Sandra's question: defective originating authority

**Status: synthetic research fixture / independent review pending.**

Sandra's challenge, as relayed by Ricky: correct enforcement of a signed decision does not establish that the original authority was justified. Tim's reported bounded receiver tests are separate work and are not reproduced here.

This follow-up to `authority.py` moves the **declared entitlement** out of the execution request and into a local SQLite table. The receiver looks up the issuer/object/destination inside its transaction rather than accepting a caller-supplied entitlement object.

## Run

```bash
python -m unittest discover -s tests -p 'test_origin_registry.py' -v
```

Ten synthetic tests are provided: positive control, signed-but-no-origin, wrong scope, revocation, replay, invalid signature, expiry, reason fidelity, zero effect on HOLD, malformed input.

## Crucial limits

- `seed_entitlement()` and `revoke()` are **unauthenticated fixture administration methods**. Anyone with access to the Python object/database can populate or alter the registry. This is **not** a protected origin-of-authority service.
- HMAC key ownership is not an independent entitlement to approve an action.
- The clock is caller-supplied. Revocation visibility and transaction ordering are simplified.
- SQLite is local. No cross-service, network, distributed revocation, crash-recovery or production guarantee.
- The `HOLD` result means **the local fixture has no matching record**, not that a real-world right is absent.
- A positive test checks the seeded fixture, not whether the original authorisation was legally, ethically or institutionally justified.
- No third-party source code, private Sandra material, or Tim's implementation is incorporated.

**Public claim ceiling:** “A local fixture demonstrates that a valid signature can be held when a separate, declared issuer-entitlement registry lacks a matching record.”

The implementation and tests are published for review. Do not claim a fresh independent execution receipt or Vector sign-off until those actually exist.

**LinkedIn: HOLD** until independent review, corrections and Ricky's separate final publication approval.
