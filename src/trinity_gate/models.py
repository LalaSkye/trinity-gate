"""Stable request and result shapes for the v0.2 vertical slice."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    HOLD = "HOLD"
    DENY = "DENY"


@dataclass(frozen=True)
class ActionRequest:
    request_id: str
    actor_id: str
    action: str
    object_id: str
    environment: str
    target: str
    payload: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ActionRequest":
        required = (
            "request_id",
            "actor_id",
            "action",
            "object_id",
            "environment",
            "target",
            "payload",
        )
        missing = [field for field in required if field not in value]
        if missing:
            raise ValueError("missing request field(s): " + ",".join(missing))
        for field in required[:-1]:
            if not isinstance(value[field], str) or not value[field]:
                raise ValueError(f"request field must be a non-empty string: {field}")
        if not isinstance(value["payload"], Mapping):
            raise ValueError("request payload must be an object")
        return cls(**{field: value[field] for field in required})

    @property
    def commit_hash(self) -> str:
        # The core's commit_hash binds fields it does not model explicitly,
        # including the exact destination and payload.
        return stable_hash(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProductResult:
    verdict: Verdict
    code: str
    request_id: str
    decision_id: str | None
    receipt_hash: str | None
    execution_id: str | None
    executed: bool
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["verdict"] = self.verdict.value
        return value

