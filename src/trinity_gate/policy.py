"""Small machine-readable policy boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Mapping

from .models import ActionRequest


@dataclass(frozen=True)
class ActionPolicy:
    environments: tuple[str, ...]
    object_prefixes: tuple[str, ...]
    requires_human_approval: bool


class Policy:
    def __init__(self, *, version: str, actions: Mapping[str, ActionPolicy]) -> None:
        if not version:
            raise ValueError("policy_version is required")
        self.version = version
        self.actions = dict(actions)

    @classmethod
    def load(cls, path: str | Path) -> "Policy":
        raw: Mapping[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_mapping(raw)

    @classmethod
    def default(cls) -> "Policy":
        raw = json.loads(
            resources.files("trinity_gate")
            .joinpath("data/policy.v0.2.json")
            .read_text(encoding="utf-8")
        )
        return cls.from_mapping(raw)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "Policy":
        if raw.get("default_verdict") != "DENY":
            raise ValueError("policy must fail closed with default_verdict DENY")
        actions: dict[str, ActionPolicy] = {}
        for name, value in raw.get("actions", {}).items():
            actions[name] = ActionPolicy(
                environments=tuple(value.get("environments", ())),
                object_prefixes=tuple(value.get("object_prefixes", ())),
                requires_human_approval=value.get("requires_human_approval") is True,
            )
        return cls(version=str(raw.get("policy_version", "")), actions=actions)

    def rejection_code(self, request: ActionRequest) -> str | None:
        rule = self.actions.get(request.action)
        if rule is None:
            return "DENY:ACTION_NOT_IN_POLICY"
        if request.environment not in rule.environments:
            return "DENY:ENVIRONMENT_NOT_IN_POLICY"
        if not any(request.object_id.startswith(prefix) for prefix in rule.object_prefixes):
            return "DENY:OBJECT_NOT_IN_POLICY"
        return None

    def requires_human_approval(self, action: str) -> bool:
        rule = self.actions.get(action)
        return True if rule is None else rule.requires_human_approval
