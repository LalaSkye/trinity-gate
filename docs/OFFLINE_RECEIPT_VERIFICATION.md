# Offline receipt export verification (additive v0.2 capability)

Trinity Gate already records simulated effects, consumed nonces and hash-linked receipts in one local SQLite transaction. This optional verifier reads a **separately exported** JSONL receipt file and recomputes each hash without trusting the runtime's own `verify_receipt_chain()` result.

## Run

```bash
python -m trinity_gate.receipt_verify path/to/receipts.jsonl
python -m unittest discover -s tests -v
```

Expected output is JSON with `integrity` (`PASS` or `FAIL`), record count, diagnostic detail and `authority_verified: false`. An empty file fails rather than establishing an empty history as proof.

## Tested controls

- Two-record valid chain accepted.
- Event modified after hashing rejected.
- Missing middle record rejected.
- Forged `PASS` text does not become authority verification.
- Empty export rejected.
- Missing file rejected.

These six controls were run locally against the additive module on 12 November 2026. **They are not evidence that the repository's full suite or CI passed after publication.**

## Claim ceiling

A `PASS` verifies **internal consistency of the supplied export**. It does not establish that the export is complete, that the signer is authorised, that the record reflects actual execution, that a receipt reason is faithful, or that the underlying system is secure. An attacker able to replace the entire export can generate a fresh consistent chain. External anchoring, independent witness evidence and source-bound authority checks are outside this feature.

This addition does not modify the existing gate, decision signing, SQLite commit boundary, or simulated email action. It does not introduce a new security primitive or establish production readiness.
