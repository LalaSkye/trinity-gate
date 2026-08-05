"""Issue a demonstration DecisionRecord for one exact request file."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trinity_gate import ActionRequest, Policy, issue_demo_decision  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/issue_demo_decision.py REQUEST.json")
    secret = os.environ.get("TRINITY_GATE_DEMO_SECRET", "").encode("utf-8")
    if len(secret) < 16:
        raise SystemExit("Set TRINITY_GATE_DEMO_SECRET to at least 16 bytes.")
    request = ActionRequest.from_mapping(
        json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    )
    policy = Policy.default()
    print(
        json.dumps(
            issue_demo_decision(
                request, policy_version=policy.version, secret=secret
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
