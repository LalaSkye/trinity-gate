"""Persistent, synthetic Lala -> Trinity -> Ricky -> Delta workflow.

No external action execution or identity authentication. SQLite provides local
transactional state and event custody, not independent authority.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class Hold(RuntimeError):
    pass


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


class Workflow:
    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(str(path), isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, stage TEXT NOT NULL, source_digest TEXT NOT NULL,
            object_id TEXT NOT NULL, destination TEXT NOT NULL,
            source_ref TEXT NOT NULL, source_version TEXT NOT NULL,
            proposed_text TEXT NOT NULL, review_digest TEXT,
            decision TEXT, decision_nonce TEXT UNIQUE
        );
        CREATE TABLE IF NOT EXISTS events (
            job_id TEXT NOT NULL, sequence INTEGER NOT NULL, kind TEXT NOT NULL,
            detail TEXT NOT NULL, previous_hash TEXT, event_hash TEXT NOT NULL,
            PRIMARY KEY(job_id, sequence), FOREIGN KEY(job_id) REFERENCES jobs(id)
        );
        """)

    @contextmanager
    def _tx(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _event(self, job_id: str, kind: str, detail: dict):
        row = self.db.execute(
            "SELECT sequence,event_hash FROM events WHERE job_id=? ORDER BY sequence DESC LIMIT 1",
            (job_id,)
        ).fetchone()
        sequence = (row["sequence"] + 1) if row else 1
        previous = row["event_hash"] if row else None
        payload = {"job_id": job_id, "sequence": sequence, "kind": kind,
                   "detail": detail, "previous_hash": previous}
        self.db.execute(
            "INSERT INTO events VALUES(?,?,?,?,?,?)",
            (job_id, sequence, kind, _json(detail), previous, _hash(payload))
        )

    def _job(self, job_id: str):
        row = self.db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise Hold("unknown workflow")
        return row

    def propose(self, *, job_id: str, object_id: str, destination: str,
                source_ref: str, source_version: str, source_digest: str, text: str):
        fields = (job_id, object_id, destination, source_ref, source_version, source_digest, text)
        if not all(isinstance(v, str) and v.strip() for v in fields):
            raise Hold("all proposal bindings required")
        with self._tx():
            if self.db.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone():
                raise Hold("job ID replay")
            self.db.execute(
                "INSERT INTO jobs(id,stage,source_digest,object_id,destination,source_ref,source_version,proposed_text) VALUES(?,?,?,?,?,?,?,?)",
                (job_id, "PROPOSED", source_digest, object_id, destination, source_ref, source_version, text)
            )
            self._event(job_id, "LALA_PROPOSED", {"proposal_hash": _hash(fields), "source_digest": source_digest})

    def review(self, job_id: str, *, observed_source_digest: str,
               source_read: bool, scope_ok: bool, attribution_ok: bool):
        with self._tx():
            row = self._job(job_id)
            if row["stage"] != "PROPOSED":
                raise Hold("review transition forbidden")
            if not isinstance(observed_source_digest, str) or not observed_source_digest:
                raise Hold("source digest required")
            accepted = (observed_source_digest == row["source_digest"]
                        and source_read is True and scope_ok is True and attribution_ok is True)
            self.db.execute("UPDATE jobs SET stage=?,review_digest=? WHERE id=?",
                            ("REVIEWED" if accepted else "HELD", observed_source_digest, job_id))
            self._event(job_id, "TRINITY_REVIEW", {"result": "CHECKED" if accepted else "HOLD",
                         "observed_digest": observed_source_digest,
                         "review_assertions_only": True})
            return "CHECKED" if accepted else "HOLD"

    def decide(self, job_id: str, *, decision: str, nonce: str,
               object_id: str, destination: str, observed_source_digest: str):
        if decision not in {"ALLOW", "HOLD", "DENY"} or not isinstance(nonce, str) or not nonce.strip():
            raise Hold("invalid decision or nonce")
        with self._tx():
            row = self._job(job_id)
            if row["stage"] != "REVIEWED":
                raise Hold("decision requires checked review")
            if (object_id != row["object_id"] or destination != row["destination"]
                    or observed_source_digest != row["source_digest"]):
                raise Hold("object, destination or source changed")
            if self.db.execute("SELECT 1 FROM jobs WHERE decision_nonce=?", (nonce,)).fetchone():
                raise Hold("replayed decision nonce")
            self.db.execute("UPDATE jobs SET stage='DECIDED',decision=?,decision_nonce=? WHERE id=?",
                            (decision, nonce, job_id))
            self._event(job_id, "RICKY_DECISION_RECORDED", {"decision": decision, "nonce_digest": _hash(nonce),
                         "identity_authenticated": False, "effect_count": 0})

    def archive(self, job_id: str):
        with self._tx():
            row = self._job(job_id)
            if row["stage"] != "DECIDED":
                raise Hold("archive transition forbidden")
            self.db.execute("UPDATE jobs SET stage='STOP' WHERE id=?", (job_id,))
            self._event(job_id, "DELTA_CUSTODY", {"decision": row["decision"], "effect_count": 0})
            self._event(job_id, "STOP", {"external_effects": 0})

    def snapshot(self, job_id: str):
        row = self._job(job_id)
        events = self.db.execute(
            "SELECT sequence,kind,detail,previous_hash,event_hash FROM events WHERE job_id=? ORDER BY sequence",
            (job_id,)
        ).fetchall()
        return {"job": dict(row), "events": [
            {"sequence": e["sequence"], "kind": e["kind"], "detail": json.loads(e["detail"]),
             "previous_hash": e["previous_hash"], "event_hash": e["event_hash"]} for e in events],
            "external_effects": 0, "identity_authenticated": False}

    def verify_chain(self, job_id: str) -> bool:
        events = self.snapshot(job_id)["events"]
        if not events:
            return False
        previous = None
        for i, e in enumerate(events, 1):
            if e["sequence"] != i or e["previous_hash"] != previous:
                return False
            payload = {"job_id": job_id, "sequence": i, "kind": e["kind"],
                       "detail": e["detail"], "previous_hash": previous}
            if e["event_hash"] != _hash(payload):
                return False
            previous = e["event_hash"]
        return True

    def close(self):
        self.db.close()
