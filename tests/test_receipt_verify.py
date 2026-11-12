"""Synthetic adversarial controls for the offline receipt verifier."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from trinity_gate.receipt_verify import verify_export


def receipt(event, previous=None, sequence=1):
    payload = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = "sha256:" + hashlib.sha256(((previous or "GENESIS") + "\n" + payload).encode()).hexdigest()
    return {"sequence": sequence, "event": event, "previous_hash": previous, "receipt_hash": digest}


class ReceiptExportTests(unittest.TestCase):
    def check(self, rows):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "receipts.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            return verify_export(path)

    def test_valid_chain(self):
        a = receipt({"verdict": "HOLD"})
        b = receipt({"verdict": "DENY"}, a["receipt_hash"], 2)
        self.assertTrue(self.check([a, b])[0])

    def test_tampered_event(self):
        a = receipt({"verdict": "DENY"})
        a["event"]["verdict"] = "ALLOW"
        self.assertFalse(self.check([a])[0])

    def test_missing_middle_record(self):
        a = receipt({"x": 1})
        b = receipt({"x": 2}, a["receipt_hash"], 2)
        c = receipt({"x": 3}, b["receipt_hash"], 3)
        self.assertFalse(self.check([a, c])[0])

    def test_forged_pass_label(self):
        a = receipt({"verdict": "PASS", "authority": "not checked"})
        ok, detail, _ = self.check([a])
        self.assertTrue(ok)
        self.assertIn("authority not verified", detail)

    def test_empty_export(self):
        self.assertFalse(self.check([])[0])

    def test_missing_file(self):
        self.assertFalse(verify_export("/path/that/does/not/exist/receipts.jsonl")[0])


if __name__ == "__main__":
    unittest.main()
