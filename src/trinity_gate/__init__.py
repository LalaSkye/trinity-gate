"""Public package surface for Trinity Gate."""

from .crypto import HMACDecisionVerifier, issue_demo_decision
from .models import ActionRequest, ProductResult, Verdict
from .policy import Policy
from .runtime import SQLiteRuntime
from .service import TrinityGateService

__version__ = "0.2.0"

__all__ = [
    "ActionRequest",
    "HMACDecisionVerifier",
    "Policy",
    "ProductResult",
    "SQLiteRuntime",
    "TrinityGateService",
    "Verdict",
    "issue_demo_decision",
    "__version__",
]

