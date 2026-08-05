"""Trinity Gate product service over the released commit-gate kernel."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from commit_gate_core import CommitGate

from .crypto import HMACDecisionVerifier
from .models import ActionRequest, ProductResult, Verdict
from .policy import Policy
from .runtime import SQLiteRuntime


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class _RollbackRequired(RuntimeError):
    def __init__(self, code: str, decision_id: str | None) -> None:
        super().__init__(code)
        self.code = code
        self.decision_id = decision_id


class _BoundAuditSink:
    """Attach the product target to the core's exact gate event."""

    def __init__(self, runtime: SQLiteRuntime, request: ActionRequest) -> None:
        self._runtime = runtime
        self._request = request

    def append(self, event: Mapping[str, Any]) -> None:
        enriched = dict(event)
        enriched["product_scope"] = {
            "request_id": self._request.request_id,
            "target": self._request.target,
            "commit_hash": self._request.commit_hash,
        }
        self._runtime.append_receipt(enriched)


class TrinityGateService:
    def __init__(
        self,
        *,
        policy: Policy,
        runtime: SQLiteRuntime,
        decision_secret: bytes,
    ) -> None:
        self.policy = policy
        self.runtime = runtime
        self._verifier = HMACDecisionVerifier(decision_secret)

    def check_action(
        self,
        request: ActionRequest,
        decision_record: Mapping[str, Any] | None = None,
    ) -> ProductResult:
        try:
            with self.runtime.transaction():
                rejection = self.policy.rejection_code(request)
                if rejection is not None:
                    receipt_hash = self.runtime.append_receipt(
                        self._control_event(request, Verdict.DENY, rejection, None)
                    )
                    return self._result(
                        request=request,
                        verdict=Verdict.DENY,
                        code=rejection,
                        decision_id=None,
                        receipt_hash=receipt_hash,
                    )

                if decision_record is None:
                    code = "HOLD:HUMAN_DECISION_REQUIRED"
                    receipt_hash = self.runtime.append_receipt(
                        self._control_event(request, Verdict.HOLD, code, None)
                    )
                    return self._result(
                        request=request,
                        verdict=Verdict.HOLD,
                        code=code,
                        decision_id=None,
                        receipt_hash=receipt_hash,
                    )

                execution_id: str | None = None

                def stage_exact_action(record: Mapping[str, Any]) -> None:
                    nonlocal execution_id
                    if request.action != "email.send":
                        raise ValueError("UNIMPLEMENTED_ACTION")
                    execution_id = self.runtime.stage_email(
                        request, decision_id=str(record["decision_id"])
                    )

                gate = CommitGate(
                    verifier=self._verifier,
                    nonce_ledger=self.runtime,
                    audit=_BoundAuditSink(self.runtime, request),
                    mutation_callback=stage_exact_action,
                    accepted_policy_versions=[self.policy.version],
                )
                core_result = gate.execute(
                    record=decision_record,
                    actor_id=request.actor_id,
                    action=request.action,
                    object_id=request.object_id,
                    environment=request.environment,
                    commit_hash=request.commit_hash,
                )

                # If the core staged an effect but could not confirm its audit
                # receipt, force the outer SQLite transaction to roll back.
                if execution_id is not None and not core_result.allowed:
                    raise _RollbackRequired(core_result.code, core_result.decision_id)

                verdict = Verdict.ALLOW if core_result.allowed else Verdict.DENY
                return self._result(
                    request=request,
                    verdict=verdict,
                    code=core_result.code,
                    decision_id=core_result.decision_id,
                    receipt_hash=self.runtime.latest_receipt_hash(),
                    execution_id=execution_id,
                )
        except _RollbackRequired as exc:
            return self._result(
                request=request,
                verdict=Verdict.DENY,
                code=exc.code,
                decision_id=exc.decision_id,
                receipt_hash=None,
            )
        except Exception as exc:
            return self._result(
                request=request,
                verdict=Verdict.DENY,
                code=f"DENY:RUNTIME_FAILURE:{type(exc).__name__}",
                decision_id=None,
                receipt_hash=None,
            )

    def _control_event(
        self,
        request: ActionRequest,
        verdict: Verdict,
        code: str,
        decision_id: str | None,
    ) -> dict[str, Any]:
        return {
            "event_type": "TRINITY_GATE_CONTROL",
            "request_id": request.request_id,
            "actor_id": request.actor_id,
            "action": request.action,
            "object_id": request.object_id,
            "environment": request.environment,
            "target": request.target,
            "commit_hash": request.commit_hash,
            "verdict": verdict.value,
            "code": code,
            "decision_id": decision_id,
            "timestamp": _timestamp(),
        }

    def _result(
        self,
        *,
        request: ActionRequest,
        verdict: Verdict,
        code: str,
        decision_id: str | None,
        receipt_hash: str | None,
        execution_id: str | None = None,
    ) -> ProductResult:
        return ProductResult(
            verdict=verdict,
            code=code,
            request_id=request.request_id,
            decision_id=decision_id,
            receipt_hash=receipt_hash,
            execution_id=execution_id,
            executed=execution_id is not None and verdict is Verdict.ALLOW,
            timestamp=_timestamp(),
        )
