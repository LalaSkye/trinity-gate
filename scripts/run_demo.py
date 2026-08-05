"""Run HOLD -> explicit decision -> ALLOW against a temporary local runtime."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trinity_gate import (  # noqa: E402
    ActionRequest,
    Policy,
    SQLiteRuntime,
    TrinityGateService,
    issue_demo_decision,
)


def main() -> None:
    secret = os.environ.get("TRINITY_GATE_DEMO_SECRET", "").encode("utf-8")
    if len(secret) < 16:
        raise SystemExit("Set TRINITY_GATE_DEMO_SECRET to at least 16 bytes.")
    request = ActionRequest.from_mapping(
        json.loads((ROOT / "examples" / "email_request.json").read_text(encoding="utf-8"))
    )
    policy = Policy.default()

    with tempfile.TemporaryDirectory(prefix="trinity-gate-demo-") as temp_dir:
        runtime = SQLiteRuntime(Path(temp_dir) / "demo.db")
        service = TrinityGateService(
            policy=policy, runtime=runtime, decision_secret=secret
        )
        held = service.check_action(request)
        record = issue_demo_decision(
            request, policy_version=policy.version, secret=secret
        )
        allowed = service.check_action(request, record)

        print(f"first verdict:  {held.verdict.value}")
        print(f"second verdict: {allowed.verdict.value}")
        print(f"outbox rows:    {runtime.outbox_count()}")
        print(f"receipt chain:  {'valid' if runtime.verify_receipt_chain() else 'invalid'}")
        runtime.close()


if __name__ == "__main__":
    main()
