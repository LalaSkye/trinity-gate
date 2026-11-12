# PRECITA Provenance Compiler v0.1

**Status:** offline synthetic prototype, not installed or a production control.

Checks **declared exact spans** as a source document passes into a target draft or handoff. It detects changed quoted text, changed numeric tokens, missing original/target spans, and a supplied attribution that differs from the source author. It fingerprints both document texts and returns a machine-readable receipt.

## Run

From the Trinity Gate repository root (Python 3.11+):

```bash
python examples/precita_compiler/compiler.py examples/precita_compiler/sample.json
python -m unittest discover -s tests -p 'test_precita_compiler.py' -v
```

The example deliberately changes 1,200 to 1,300, so the command returns HOLD (exit code 1). Exit code 0 means all *declared* bindings CHECKED. Invalid inputs return exit code 2. The tool has no network calls and does not write files.

## Input contract

`source` and `target`: each has `id`, `version`, `author`, `text` (nonempty strings).

`bindings`: array of `{id, kind, original, rendered, attributed_to}`. `kind` is `quote`, `number`, or `attribution`.

The original and rendered strings must appear in their respective documents. Quote comparisons are byte-for-byte Unicode string comparisons; number comparisons use lexical number tokens, not arithmetic or unit conversion. `attributed_to` must equal the source author.

## Proof and limits

- Ten synthetic unit tests were run locally before publication, including changed quote, changed number, wrong author, missing source span, missing target span, duplicate binding and empty coverage.
- **Coverage is always incomplete** in v0.1: only user-declared spans are checked. Omitted claims and material losses outside bindings are invisible.
- `CHECKED` is not evidence of semantic equivalence, truth, independent source inspection, consent, or authority.
- A malicious or mistaken user can supply false source text or omit a binding. Hashes identify the provided text only.
- No real private source files, Sandra messages, account data or external services are used.
- No semantic analysis, translation quality assessment, PDF parsing, XLSX parsing or model calls.
- The `attribution` kind checks existence and the declared author, not whether an attribution is justified by independent evidence.

## Existing research, not a novelty claim

Design bounded by [PRECITA Safe Passage Binding Principle](https://app.notion.com/p/3c9276e494c481d683f1d476a38a71c3), [PRECITA Enforcement Test](https://app.notion.com/p/3e8276e494c481c9901cca562ffc753d) and the existing [Snapshot Comparator build brief](https://docs.google.com/document/d/1JWAh-vtgAbFF9L4T7FhWWhfTBXzTzro-QF3sG0g151Q/edit). The Snapshot Comparator is a separate proposal for comparing overlapping analytics exports. This compiler addresses explicitly bound text passages.

**STOP:** No automatic publication of transformed documents, no real-world effect and no authority transfer.
