"""Atomic SQLite custody for nonces, simulated effects and receipts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from .models import ActionRequest, canonical_json


class SQLiteRuntime:
    def __init__(self, path: str | Path = ":memory:") -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._in_transaction = False
        self._create_schema()

    def _create_schema(self) -> None:
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS consumed_nonces (
                nonce TEXT PRIMARY KEY,
                decision_id TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS email_outbox (
                execution_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                decision_id TEXT NOT NULL,
                target TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS receipts (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                payload_json TEXT NOT NULL,
                previous_hash TEXT,
                receipt_hash TEXT NOT NULL UNIQUE
            );
            """
        )
        self._db.commit()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self._lock:
            if self._in_transaction:
                raise RuntimeError("nested runtime transaction")
            self._db.execute("BEGIN IMMEDIATE")
            self._in_transaction = True
            try:
                yield
            except Exception:
                self._db.rollback()
                raise
            else:
                self._db.commit()
            finally:
                self._in_transaction = False

    def contains(self, nonce: str) -> bool:
        row = self._db.execute(
            "SELECT 1 FROM consumed_nonces WHERE nonce = ?", (nonce,)
        ).fetchone()
        return row is not None

    def consume(self, nonce: str, decision_id: str) -> None:
        self._db.execute(
            "INSERT INTO consumed_nonces(nonce, decision_id) VALUES (?, ?)",
            (nonce, decision_id),
        )

    def rollback(self, nonce: str, decision_id: str) -> None:
        self._db.execute(
            "DELETE FROM consumed_nonces WHERE nonce = ? AND decision_id = ?",
            (nonce, decision_id),
        )

    def append(self, event: Mapping[str, Any]) -> None:
        self.append_receipt(event)

    def append_receipt(self, event: Mapping[str, Any]) -> str:
        previous = self.latest_receipt_hash()
        payload_json = canonical_json(dict(event))
        material = (previous or "GENESIS") + "\n" + payload_json
        receipt_hash = "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()
        self._db.execute(
            "INSERT INTO receipts(payload_json, previous_hash, receipt_hash) VALUES (?, ?, ?)",
            (payload_json, previous, receipt_hash),
        )
        return receipt_hash

    def latest_receipt_hash(self) -> str | None:
        row = self._db.execute(
            "SELECT receipt_hash FROM receipts ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        return None if row is None else str(row["receipt_hash"])

    def stage_email(self, request: ActionRequest, decision_id: str) -> str:
        execution_id = "exec_" + uuid.uuid4().hex
        self._db.execute(
            """
            INSERT INTO email_outbox(
                execution_id, request_id, decision_id, target, payload_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                execution_id,
                request.request_id,
                decision_id,
                request.target,
                canonical_json(dict(request.payload)),
            ),
        )
        return execution_id

    def outbox_count(self) -> int:
        row = self._db.execute("SELECT COUNT(*) AS count FROM email_outbox").fetchone()
        return int(row["count"])

    def receipt_count(self) -> int:
        row = self._db.execute("SELECT COUNT(*) AS count FROM receipts").fetchone()
        return int(row["count"])

    def receipt_events(self) -> list[dict[str, Any]]:
        rows = self._db.execute(
            """
            SELECT sequence, payload_json, previous_hash, receipt_hash
            FROM receipts ORDER BY sequence
            """
        ).fetchall()
        return [
            {
                "sequence": int(row["sequence"]),
                "event": json.loads(str(row["payload_json"])),
                "previous_hash": row["previous_hash"],
                "receipt_hash": str(row["receipt_hash"]),
            }
            for row in rows
        ]

    def export_receipts(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        lines = [canonical_json(event) for event in self.receipt_events()]
        destination.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return destination

    def verify_receipt_chain(self) -> bool:
        previous: str | None = None
        rows = self._db.execute(
            "SELECT payload_json, previous_hash, receipt_hash FROM receipts ORDER BY sequence"
        ).fetchall()
        for row in rows:
            if row["previous_hash"] != previous:
                return False
            material = (previous or "GENESIS") + "\n" + str(row["payload_json"])
            expected = "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()
            if not _constant_time_equal(expected, str(row["receipt_hash"])):
                return False
            previous = str(row["receipt_hash"])
        return True

    def close(self) -> None:
        self._db.close()


def _constant_time_equal(left: str, right: str) -> bool:
    import hmac

    return hmac.compare_digest(left, right)
