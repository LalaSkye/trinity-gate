"""Demonstration-only DecisionRecord signing and verification."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from .models import ActionRequest, canonical_json


def _unsigned_record(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key != "signature"}


def _signature(secret: bytes, record: Mapping[str, Any]) -> str:
    digest = hmac.new(
        secret,
        canonical_json(_unsigned_record(record)).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "hmac-sha256:" + digest


class HMACDecisionVerifier:
    """Local demonstration verifier; not an enterprise identity boundary."""

    def __init__(self, secret: bytes) -> None:
        if len(secret) < 16:
            raise ValueError("demo secret must contain at least 16 bytes")
        self._secret = secret

    def verify(self, record: Mapping[str, Any]) -> bool:
        supplied = record.get("signature")
        return isinstance(supplied, str) and hmac.compare_digest(
            supplied, _signature(self._secret, record)
        )


def issue_demo_decision(
    request: ActionRequest,
    *,
    policy_version: str,
    secret: bytes,
    ttl_seconds: int = 300,
    now: datetime | None = None,
) -> dict[str, str]:
    """Simulate one explicit human approval for the exact request."""

    if ttl_seconds < 1:
        raise ValueError("ttl_seconds must be positive")
    issued = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    expires = issued + timedelta(seconds=ttl_seconds)
    record: dict[str, str] = {
        "decision_id": "dec_" + uuid.uuid4().hex,
        "actor_id": request.actor_id,
        "action": request.action,
        "object_id": request.object_id,
        "environment": request.environment,
        "commit_hash": request.commit_hash,
        "verdict": "ALLOW",
        "policy_version": policy_version,
        "issued_at": issued.isoformat().replace("+00:00", "Z"),
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
        "nonce": "nonce_" + uuid.uuid4().hex,
    }
    record["signature"] = _signature(secret, record)
    return record

