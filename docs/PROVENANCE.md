# Provenance and evidence boundary

## Runtime dependency

- Object: `commit-gate-core`
- Repository: `LalaSkye/commit-gate-core`
- Release: `v0.1.1`
- Public package version: `0.1.1`
- Relationship: imported dependency; gate logic is not copied into this repo

The local verification workspace used source fetched from the tagged public
package surface. That temporary copy is excluded from this repository.

## Design inputs

The following private inspection records constrained the vertical slice but are
not bundled, published or promoted by it:

- Executive Handoff and Frame Preflight Mapping Record v0.1
- NANOBOT v1.9b Preflight Risk Pack
- Trinity Read-Only Baseline Regression Pack v0.2

The carried rules were limited to the demonstrated route:

- interpretation and a successful outcome do not create authority;
- missing effect-bearing authority produces `HOLD`;
- changed scope, state, target or freshness is rechecked;
- a receipt does not authorise a new transition;
- action, nonce and receipt custody share one atomic transaction.

These sources are design and inspection inputs. They are not independent
validation, certification or permission to expand the claim.

