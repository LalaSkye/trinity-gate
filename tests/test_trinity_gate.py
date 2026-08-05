from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

from trinity_gate import (
    ActionRequest,
    Policy,
    SQLiteRuntime,
    TrinityGateService,
    Verdict,
    issue_demo_decision,
)
from trinity_gate.http_api import evaluate_payload, make_handler


ROOT = Path(__file__).resolve().parents[1]
SECRET = b"test-secret-at-least-16-bytes"


class TrinityGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="trinity-gate-test-")
        self.runtime = SQLiteRuntime(Path(self.temp.name) / "runtime.db")
        self.policy = Policy.default()
        self.service = TrinityGateService(
            policy=self.policy,
            runtime=self.runtime,
            decision_secret=SECRET,
        )
        self.request = ActionRequest(
            request_id="req_test_001",
            actor_id="agent:test",
            action="email.send",
            object_id="email:test",
            environment="demo",
            target="person@example.invalid",
            payload={"subject": "Test", "body": "Local only"},
        )

    def tearDown(self) -> None:
        self.runtime.close()
        self.temp.cleanup()

    def decision(self, request: ActionRequest | None = None, **kwargs: object) -> dict[str, str]:
        return issue_demo_decision(
            request or self.request,
            policy_version=self.policy.version,
            secret=SECRET,
            **kwargs,
        )

    def test_missing_decision_holds_without_effect(self) -> None:
        result = self.service.check_action(self.request)
        self.assertEqual(Verdict.HOLD, result.verdict)
        self.assertFalse(result.executed)
        self.assertEqual(0, self.runtime.outbox_count())
        self.assertIsNotNone(result.receipt_hash)

    def test_exact_current_decision_allows_once(self) -> None:
        result = self.service.check_action(self.request, self.decision())
        self.assertEqual(Verdict.ALLOW, result.verdict)
        self.assertTrue(result.executed)
        self.assertEqual(1, self.runtime.outbox_count())
        self.assertTrue(self.runtime.verify_receipt_chain())

    def test_replayed_decision_is_denied(self) -> None:
        record = self.decision()
        first = self.service.check_action(self.request, record)
        second = self.service.check_action(self.request, record)
        self.assertEqual(Verdict.ALLOW, first.verdict)
        self.assertEqual(Verdict.DENY, second.verdict)
        self.assertIn("NONCE_REPLAYED", second.code)
        self.assertEqual(1, self.runtime.outbox_count())

    def test_changed_target_is_denied(self) -> None:
        record = self.decision()
        changed = replace(self.request, target="other@example.invalid")
        result = self.service.check_action(changed, record)
        self.assertEqual(Verdict.DENY, result.verdict)
        self.assertIn("SCOPE_MISMATCH:commit_hash", result.code)
        self.assertEqual(0, self.runtime.outbox_count())

    def test_changed_payload_is_denied(self) -> None:
        record = self.decision()
        changed = replace(self.request, payload={"subject": "Changed", "body": "Local only"})
        result = self.service.check_action(changed, record)
        self.assertEqual(Verdict.DENY, result.verdict)
        self.assertEqual(0, self.runtime.outbox_count())

    def test_expired_decision_is_denied(self) -> None:
        issued = datetime.now(timezone.utc) - timedelta(minutes=10)
        record = self.decision(now=issued, ttl_seconds=60)
        result = self.service.check_action(self.request, record)
        self.assertEqual(Verdict.DENY, result.verdict)
        self.assertIn("DECISION_EXPIRED", result.code)
        self.assertEqual(0, self.runtime.outbox_count())

    def test_policy_rejects_unknown_action_before_core(self) -> None:
        request = replace(self.request, action="file.delete")
        result = self.service.check_action(request)
        self.assertEqual(Verdict.DENY, result.verdict)
        self.assertEqual("DENY:ACTION_NOT_IN_POLICY", result.code)
        self.assertEqual(0, self.runtime.outbox_count())

    def test_bad_signature_is_denied(self) -> None:
        record = self.decision()
        record["signature"] = "hmac-sha256:" + ("0" * 64)
        result = self.service.check_action(self.request, record)
        self.assertEqual(Verdict.DENY, result.verdict)
        self.assertIn("INVALID_SIGNATURE", result.code)

    def test_audit_failure_rolls_back_staged_effect(self) -> None:
        original = self.runtime.append_receipt

        def fail_receipt(event: object) -> str:
            raise OSError("synthetic receipt failure")

        self.runtime.append_receipt = fail_receipt  # type: ignore[method-assign]
        result = self.service.check_action(self.request, self.decision())
        self.runtime.append_receipt = original  # type: ignore[method-assign]
        self.assertEqual(Verdict.DENY, result.verdict)
        self.assertIn("AUDIT_APPEND_FAILED", result.code)
        self.assertFalse(result.executed)
        self.assertEqual(0, self.runtime.outbox_count())
        self.assertEqual(0, self.runtime.receipt_count())

    def test_receipt_chain_detects_tampering(self) -> None:
        self.service.check_action(self.request)
        self.assertTrue(self.runtime.verify_receipt_chain())
        self.runtime._db.execute(  # bounded corruption specimen
            "UPDATE receipts SET payload_json = ? WHERE sequence = 1", ("{}",)
        )
        self.runtime._db.commit()
        self.assertFalse(self.runtime.verify_receipt_chain())

    def test_receipt_export_keeps_exact_target_and_chain_hash(self) -> None:
        result = self.service.check_action(self.request, self.decision())
        destination = Path(self.temp.name) / "receipts.jsonl"
        self.runtime.export_receipts(destination)
        exported = [json.loads(line) for line in destination.read_text().splitlines()]
        self.assertEqual(self.request.target, exported[0]["event"]["product_scope"]["target"])
        self.assertEqual(result.receipt_hash, exported[0]["receipt_hash"])

    def test_http_payload_surface_returns_product_result(self) -> None:
        status, body = evaluate_payload(
            self.service, {"request": self.request.to_dict()}
        )
        self.assertEqual(200, status)
        self.assertEqual("HOLD", body["verdict"])

    def test_invalid_http_payload_fails_closed(self) -> None:
        status, body = evaluate_payload(self.service, {"request": {}})
        self.assertEqual(400, status)
        self.assertEqual("DENY", body["verdict"])

    def test_live_http_endpoint_returns_hold(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.service))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            encoded = json.dumps({"request": self.request.to_dict()}).encode("utf-8")
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_port}/v1/check",
                data=encoded,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=2) as response:
                body = json.loads(response.read())
            self.assertEqual("HOLD", body["verdict"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
