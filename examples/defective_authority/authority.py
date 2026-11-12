"""Synthetic issuer-entitlement gate: valid HMAC is necessary but insufficient."""
from __future__ import annotations
import hashlib
import hmac
import json
import sqlite3
from dataclasses import dataclass
from typing import Optional

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()

def sign(secret: bytes, record: dict) -> str:
    return hmac.new(secret, canonical(record), hashlib.sha256).hexdigest()

@dataclass(frozen=True)
class Result:
    verdict: str
    reason: str
    effects: int

class Gate:
    """Single SQLite connection; simulated effect committed with nonce consumption."""
    def __init__(self, secret: bytes, db: Optional[sqlite3.Connection] = None):
        self.secret = secret
        self.db = db or sqlite3.connect(':memory:', isolation_level=None)
        self.db.execute('CREATE TABLE IF NOT EXISTS used (nonce TEXT PRIMARY KEY)')
        self.db.execute('CREATE TABLE IF NOT EXISTS effects (nonce TEXT PRIMARY KEY, object_id TEXT, destination TEXT)')

    def execute(self, record: dict, signature: str, *, entitlement: Optional[dict], now: int) -> Result:
        # Only locally supplied synthetic records are used. No remote issuer authentication.
        if not isinstance(record, dict) or set(record) != {'issuer', 'object_id', 'destination', 'nonce', 'expires_at'}:
            return Result('DENY', 'MALFORMED_RECORD', self.count())
        if not all(isinstance(record[k], str) and record[k] for k in ('issuer', 'object_id', 'destination', 'nonce')) or type(record['expires_at']) is not int:
            return Result('DENY', 'MALFORMED_RECORD', self.count())
        if not isinstance(signature, str) or not hmac.compare_digest(sign(self.secret, record), signature):
            return Result('DENY', 'INVALID_SIGNATURE', self.count())
        if now >= record['expires_at']:
            return Result('DENY', 'EXPIRED_RECORD', self.count())
        if entitlement is None:
            return Result('HOLD', 'ORIGIN_AUTHORITY_UNPROVEN', self.count())
        if not isinstance(entitlement, dict) or set(entitlement) != {'issuer', 'object_id', 'destination', 'active', 'revoked_at'}:
            return Result('DENY', 'INVALID_ENTITLEMENT', self.count())
        if entitlement['issuer'] != record['issuer'] or entitlement['object_id'] != record['object_id'] or entitlement['destination'] != record['destination']:
            return Result('DENY', 'ISSUER_NOT_ENTITLED_FOR_SCOPE', self.count())
        if entitlement['active'] is not True:
            return Result('DENY', 'ISSUER_NOT_ENTITLED_FOR_SCOPE', self.count())
        if entitlement['revoked_at'] is not None and now >= entitlement['revoked_at']:
            return Result('DENY', 'ISSUER_AUTHORITY_REVOKED', self.count())
        try:
            self.db.execute('BEGIN IMMEDIATE')
            if self.db.execute('SELECT 1 FROM used WHERE nonce=?', (record['nonce'],)).fetchone():
                self.db.execute('ROLLBACK')
                return Result('DENY', 'REPLAYED_DECISION', self.count())
            self.db.execute('INSERT INTO used VALUES (?)', (record['nonce'],))
            self.db.execute('INSERT INTO effects VALUES (?,?,?)', (record['nonce'], record['object_id'], record['destination']))
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise
        return Result('ALLOW', 'SYNTHETIC_EFFECT_COMMITTED', self.count())

    def count(self):
        return self.db.execute('SELECT COUNT(*) FROM effects').fetchone()[0]
