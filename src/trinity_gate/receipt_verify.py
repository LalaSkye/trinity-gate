"""Offline integrity check for Trinity Gate JSONL receipt exports.

Checks local hash links, not authority, signatures, external completeness or effects.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any


def verify_export(path: str | Path) -> tuple[bool, str, int]:
    previous: str | None = None
    count = 0
    try:
        with Path(path).open("r", encoding="utf-8") as source:
            for line_no, line in enumerate(source, 1):
                if not line.strip():
                    return False, f"blank line {line_no}", count
                try:
                    row: Any = json.loads(line)
                except (ValueError, TypeError):
                    return False, f"invalid JSON at line {line_no}", count
                if not isinstance(row, dict) or set(row) != {"sequence", "event", "previous_hash", "receipt_hash"}:
                    return False, f"invalid receipt shape at line {line_no}", count
                if type(row["sequence"]) is not int or row["sequence"] != line_no:
                    return False, f"non-contiguous sequence at line {line_no}", count
                if not isinstance(row["event"], dict) or not isinstance(row["receipt_hash"], str):
                    return False, f"invalid event/hash at line {line_no}", count
                if row["previous_hash"] != previous:
                    return False, f"broken predecessor at line {line_no}", count
                payload = json.dumps(row["event"], sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                expected = "sha256:" + hashlib.sha256(((previous or "GENESIS") + "\n" + payload).encode("utf-8")).hexdigest()
                if not hmac.compare_digest(expected, row["receipt_hash"]):
                    return False, f"hash mismatch at line {line_no}", count
                previous = row["receipt_hash"]
                count += 1
    except (OSError, UnicodeError) as exc:
        return False, f"unreadable export: {type(exc).__name__}", count
    if count == 0:
        return False, "empty export cannot establish a receipt history", 0
    return True, "hash links and sequences consistent; authority not verified", count


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Trinity Gate JSONL receipt integrity")
    parser.add_argument("export", help="JSONL file produced by SQLiteRuntime.export_receipts")
    args = parser.parse_args()
    ok, reason, count = verify_export(args.export)
    print(json.dumps({"integrity": "PASS" if ok else "FAIL", "records": count, "detail": reason, "authority_verified": False}, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
