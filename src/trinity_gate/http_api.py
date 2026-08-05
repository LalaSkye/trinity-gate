"""Dependency-light JSON-over-HTTP surface for the local vertical slice."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping

from .models import ActionRequest
from .policy import Policy
from .runtime import SQLiteRuntime
from .service import TrinityGateService


def evaluate_payload(
    service: TrinityGateService, payload: Mapping[str, Any]
) -> tuple[int, dict[str, Any]]:
    try:
        request_value = payload.get("request")
        if not isinstance(request_value, Mapping):
            raise ValueError("request must be an object")
        request = ActionRequest.from_mapping(request_value)
        decision = payload.get("decision_record")
        if decision is not None and not isinstance(decision, Mapping):
            raise ValueError("decision_record must be an object")
        return 200, service.check_action(request, decision).to_dict()
    except ValueError as exc:
        return 400, {"verdict": "DENY", "code": "DENY:INVALID_REQUEST", "detail": str(exc)}


def make_handler(service: TrinityGateService) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/health":
                self._reply(404, {"status": "not_found"})
                return
            self._reply(200, {"status": "ok", "policy_version": service.policy.version})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/check":
                self._reply(404, {"status": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 1_000_000:
                    raise ValueError("body size is invalid")
                value = json.loads(self.rfile.read(length))
                if not isinstance(value, Mapping):
                    raise ValueError("body must be an object")
                status, body = evaluate_payload(service, value)
            except (ValueError, json.JSONDecodeError) as exc:
                status, body = 400, {
                    "verdict": "DENY",
                    "code": "DENY:INVALID_JSON",
                    "detail": str(exc),
                }
            self._reply(status, body)

        def _reply(self, status: int, body: Mapping[str, Any]) -> None:
            encoded = json.dumps(body, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def build_service_from_env() -> TrinityGateService:
    secret = os.environ.get("TRINITY_GATE_DEMO_SECRET", "").encode("utf-8")
    if len(secret) < 16:
        raise RuntimeError("TRINITY_GATE_DEMO_SECRET must contain at least 16 bytes")
    root = Path(__file__).resolve().parents[2]
    policy_path = os.environ.get("TRINITY_GATE_POLICY")
    db_path = os.environ.get("TRINITY_GATE_DB", str(root / "runtime" / "trinity-gate.db"))
    return TrinityGateService(
        policy=Policy.load(policy_path) if policy_path else Policy.default(),
        runtime=SQLiteRuntime(db_path),
        decision_secret=secret,
    )


def main() -> None:
    service = build_service_from_env()
    host = os.environ.get("TRINITY_GATE_HOST", "127.0.0.1")
    port = int(os.environ.get("TRINITY_GATE_PORT", "8080"))
    server = ThreadingHTTPServer((host, port), make_handler(service))
    print(f"Trinity Gate listening on http://{host}:{port}")
    try:
        server.serve_forever()
    finally:
        service.runtime.close()


if __name__ == "__main__":
    main()
