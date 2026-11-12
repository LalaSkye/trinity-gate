# Defective Authority Test v0.1

**Synthetic demonstration. Not a live authority verifier.**

A technically valid HMAC signature does not establish that the issuer had legitimate authority. This test separates signature validity, declared issuer entitlement, expiry, revocation, nonce replay and local effect commitment. It tests **reason fidelity**, not just denial.

## Run

From the repository root with Python 3.11+:

```bash
python -m unittest discover -s tests -p 'test_defective_authority.py' -v
```

Ten tests were executed locally before publication: valid positive control, valid signature with wrong issuer, wrong destination, revoked entitlement, replayed nonce, absent originating evidence, bad signature, expiry, wrong-reason prevention and malformed record. Local result: `Ran 10 tests ... OK`.

## Behaviour

- Signed record + matching active entitlement + unused nonce → `ALLOW`, one **local SQLite** effect row.
- Signed record but wrong issuer/object/destination entitlement → `DENY:ISSUER_NOT_ENTITLED_FOR_SCOPE`, zero effects.
- Signed record with missing entitlement → `HOLD:ORIGIN_AUTHORITY_UNPROVEN`.
- Revoked entitlement → `DENY:ISSUER_AUTHORITY_REVOKED`.
- Replayed nonce → `DENY:REPLAYED_DECISION`, no second effect.

## Important limitations

1. The entitlement object is **caller-supplied**. It is not authenticated, independently justified or sourced from a real authority registry.
2. All signatures use a single local HMAC secret. Anyone with the secret can issue demonstration records. This is **not** an independent issuer identity system.
3. The clock is caller-supplied; expiry and revocation are only synthetic checks.
4. The SQLite transaction is local, single-connection and illustrative. No distributed atomicity, crash-safety proof, external service, or real email delivery.
5. The tool does not establish that any real-world authority was legitimate, or reproduce Tim's implementation or reported tests.
6. The conceptual distinction was raised by Sandra in a user-supplied discussion. This implementation is a separate synthetic test and does not claim her authorship or Tim's results.
7. No production security assurance, compliance certification or novelty claim.

**Status:** Published review candidate. Independent review and repository-wide CI not verified. No LinkedIn publication authorised.
