# Trinity Gate v0.2 Product Boundary

## Object

One local vertical slice proving this sequence:

1. an agent proposes an exact action;
2. policy eligibility is checked;
3. missing human authority produces `HOLD`;
4. invalid, stale, replayed or mismatched authority produces `DENY`;
5. exact current authority permits one simulated effect;
6. the verdict and effect are recorded in one SQLite transaction;
7. the receipt chain can be independently rechecked.

## Authority model

The runtime never creates authority from a successful outcome or an earlier
receipt. Every permitted action requires a current, one-use `DecisionRecord`
whose signature and scope match the proposed action.

The demonstration signer is HMAC-based. It is not a production identity
system. Whoever holds the local secret can issue demonstration records.

## Custody model

The SQLite runtime stores:

- consumed nonces;
- simulated email outbox rows;
- hash-chained gate receipts.

These are committed or rolled back together. Hash chaining makes alteration
detectable when the chain is verified; it does not make the database immutable.

## Stop boundary

This repository stops at one simulated `email.send` route. It does not connect
to Gmail, Outlook, SMTP, cloud infrastructure or a production agent.

No framework mapping in the source inspection packs is promoted to a compliance
claim by this implementation.

