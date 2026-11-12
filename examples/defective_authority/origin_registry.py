"""Synthetic authority-origin registry, separate from record signature verification.

An administrator seeds entitlements before execution. The caller cannot supply
entitlement data to the receiver. This is not real-world authority proof.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import sqlite3

def _wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def sign(key: bytes, record: dict) -> str:
    return hmac.new(key, _wire(record), hashlib.sha256).hexdigest()

class OriginGate:
    def __init__(self, signing_key: bytes, path=":memory:"):
        self.key = signing_key
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS authority(
          issuer TEXT, object_id TEXT, destination TEXT,
          active INTEGER NOT NULL, revoked_at INTEGER,
          PRIMARY KEY(issuer,object_id,destination));
        CREATE TABLE IF NOT EXISTS used(nonce TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS effects(nonce TEXT PRIMARY KEY, object_id TEXT, destination TEXT);
        """)

    def seed_entitlement(self, *, issuer, object_id, destination):
        """Fixture setup only. NOT a protected administration API."""
        self.db.execute("INSERT INTO authority VALUES(?,?,?,1,NULL)", (issuer, object_id, destination))

    def revoke(self, *, issuer, object_id, destination, at):
        """Fixture setup only. Caller is not authenticated."""
        self.db.execute("UPDATE authority SET active=0, revoked_at=? WHERE issuer=? AND object_id=? AND destination=?",
                        (at, issuer, object_id, destination))

    def execute(self, record, signature, now):
        required = {"issuer", "object_id", "destination", "nonce", "expires_at"}
        if not isinstance(record, dict) or set(record) != required or any(
            not isinstance(record[k], str) or not record[k] for k in required - {"expires_at"}
        ) or type(record["expires_at"]) is not int or type(now) is not int:
            return "DENY:MALFORMED_RECORD"
        if not isinstance(signature, str) or not hmac.compare_digest(sign(self.key, record), signature):
            return "DENY:INVALID_SIGNATURE"
        self.db.execute("BEGIN IMMEDIATE")
        try:
            if now >= record["expires_at"]:
                result = "DENY:EXPIRED"
            else:
                row = self.db.execute(
                    "SELECT active,revoked_at FROM authority WHERE issuer=? AND object_id=? AND destination=?",
                    (record["issuer"], record["object_id"], record["destination"])
                ).fetchone()
                if row is None:
                    result = "HOLD:ORIGIN_NOT_ESTABLISHED"
                elif row[1] is not None and now >= row[1]:
                    result = "DENY:REVOKED"
                elif row[0] != 1:
                    result = "DENY:INACTIVE"
                elif self.db.execute("SELECT 1 FROM used WHERE nonce=?", (record["nonce"],)).fetchone():
                    result = "DENY:REPLAY"
                else:
                    self.db.execute("INSERT INTO used VALUES(?)", (record["nonce"],))
                    self.db.execute("INSERT INTO effects VALUES(?,?,?)",
                                    (record["nonce"], record["object_id"], record["destination"]))
                    result = "ALLOW:SIMULATED_EFFECT"
            self.db.execute("COMMIT")
            return result
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def effect_count(self):
        return self.db.execute("SELECT COUNT(*) FROM effects").fetchone()[0]
