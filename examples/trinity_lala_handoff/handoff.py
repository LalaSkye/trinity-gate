"""Source-bound, non-executing Lala -> Trinity -> Ricky -> Delta handoff."""
import hashlib
import json
from dataclasses import dataclass
from typing import Any

STAGES = ("LALA_DRAFT", "TRINITY_REVIEW", "RICKY_DECISION", "DELTA_ARCHIVE", "STOP")
REQUIRED = ("object_id", "source", "source_version", "speaker", "author", "recipient", "destination", "content", "requested_action", "claim_ceiling", "stop_condition")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


@dataclass
class Handoff:
    payload: dict
    events: list

    @classmethod
    def begin(cls, payload):
        if not isinstance(payload, dict):
            raise ValueError("payload must be object")
        missing = [k for k in REQUIRED if not isinstance(payload.get(k), str) or not payload[k].strip()]
        if missing:
            raise ValueError("missing fields: " + ", ".join(missing))
        item = cls(dict(payload), [])
        item._append("LALA_DRAFT", "Lala", "PROPOSED", "Candidate words only; no authority transferred")
        return item

    def _append(self, stage, actor, verdict, note):
        previous = self.events[-1]["hash"] if self.events else None
        event = {"sequence": len(self.events) + 1, "stage": stage, "actor": actor, "verdict": verdict,
                 "note": note, "payload_hash": digest(self.payload), "previous_hash": previous}
        event["hash"] = digest(event)
        self.events.append(event)

    def review(self, *, evidence_read, scope_ok, attribution_ok, reviewer="Trinity"):
        if self.events[-1]["stage"] != "LALA_DRAFT":
            raise ValueError("invalid transition")
        if reviewer != "Trinity":
            raise ValueError("wrong reviewer")
        verdict = "PASS" if all((evidence_read, scope_ok, attribution_ok)) else "HOLD"
        self._append("TRINITY_REVIEW", "Trinity", verdict, "Review only; PASS does not authorise action")
        return verdict

    def decide(self, *, decision, approver="Ricky", object_id=None, destination=None):
        if self.events[-1]["stage"] != "TRINITY_REVIEW":
            raise ValueError("invalid transition")
        if approver != "Ricky":
            raise ValueError("live human authority required")
        if decision not in ("ALLOW", "HOLD", "DENY"):
            raise ValueError("unknown decision")
        if decision == "ALLOW" and (
            self.events[-1]["verdict"] != "PASS" or object_id != self.payload["object_id"]
            or destination != self.payload["destination"]
        ):
            raise ValueError("ALLOW must bind reviewed object and destination")
        self._append("RICKY_DECISION", "Ricky", decision, "Recorded decision only; no action executed")

    def archive(self):
        if self.events[-1]["stage"] != "RICKY_DECISION":
            raise ValueError("invalid transition")
        self._append("DELTA_ARCHIVE", "Delta", "RECORDED", "Local custody receipt, not independent verification")
        self._append("STOP", "System", "STOP", "No send, publish, deployment or persistence beyond local export")

    def export(self):
        return {"schema": "trinity-lala-handoff/0.1", "payload": self.payload, "events": self.events, "effect_count": 0}


def verify(record):
    if not isinstance(record, dict) or record.get("schema") != "trinity-lala-handoff/0.1" or record.get("effect_count") != 0:
        return False
    payload, events = record.get("payload"), record.get("events")
    if not isinstance(payload, dict) or not isinstance(events, list) or not events or len(events) > len(STAGES):
        return False
    previous = None
    for i, event in enumerate(events):
        if not isinstance(event, dict) or type(event.get("sequence")) is not int or event["sequence"] != i + 1:
            return False
        if event.get("previous_hash") != previous or event.get("payload_hash") != digest(payload):
            return False
        if event.get("stage") != STAGES[i]:
            return False
        actual = event.get("hash")
        if not isinstance(actual, str) or actual != digest({k: v for k, v in event.items() if k != "hash"}):
            return False
        previous = actual
    if events[0]["actor"] != "Lala" or events[0]["verdict"] != "PROPOSED":
        return False
    if len(events) > 1 and (events[1]["actor"] != "Trinity" or events[1]["verdict"] not in ("PASS", "HOLD")):
        return False
    if len(events) > 2:
        decision = events[2]
        if decision["actor"] != "Ricky" or decision["verdict"] not in ("ALLOW", "HOLD", "DENY"):
            return False
        if decision["verdict"] == "ALLOW" and events[1]["verdict"] != "PASS":
            return False
    if len(events) > 3 and (events[3]["actor"] != "Delta" or events[3]["verdict"] != "RECORDED"):
        return False
    if len(events) > 4 and events[4]["verdict"] != "STOP":
        return False
    return True
