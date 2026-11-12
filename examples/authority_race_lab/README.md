# Trinity Authority Race Lab v0.1

A deterministic, synthetic interleaving explorer demonstrating the **check-to-effect revocation race**. It is an additive example in Trinity Gate, not a distributed-systems proof or production gate.

## Run

From the repository root with Python 3.11+:

```bash
python examples/authority_race_lab/race_lab.py
python -m unittest discover -s tests -p 'test_authority_race_lab.py' -v
```

## Model

Two actors A and B each perform `check` then `commit`. A single `revoke` may occur between any events. We exhaustively enumerate the 30 valid total orders of five events.

- `unsafe_cache`: an earlier successful check remains sufficient for the later effect.
- `effect_recheck`: a commit requires both its earlier check and authority still active at the commit boundary.

**Observed locally before publication:** 30 schedules; 16 with stale effects under cached checks; zero under effect-time recheck; nine unit tests passed.

## Important limitations

- The model is **sequential**, not a real concurrent runtime. It does not execute threads, transactions or remote services.
- Revocation is instantaneous and globally visible *by assumption*. Real distributed systems have propagation delays, fencing epochs and competing semantics of revocation.
- There is no network, clock, lease, escrow, retry, crash or independent verifier.
- This does not prove revocation safety in the existing Trinity Gate implementation.
- The project makes no novelty, security certification or production-readiness claim.

## Design context

The example addresses the check-to-effect race from TrinityOS's candidate pre-build checklist. Prior research closed the cross-domain authority contradiction candidate as **PRIOR ART / NO NOVELTY ESTABLISHED**. This fixture illustrates a known failure mode rather than reopening that claim.

## STOP

Synthetic, read-only demonstration. No external effects, no deployment and no authority transfer.
