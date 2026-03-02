"""ConsumerConstraintHandlerProvider -- AuditTrailHandler.

Handles obligations/advice of type "auditTrail".
Receives the response value AFTER the endpoint method returns and
records it to an in-memory audit log. The response itself is NOT modified
(consumers are side-effect only).

Policy obligation example:
  { "type": "auditTrail", "action": "readMedicalRecord" }
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import structlog

log = structlog.get_logger()


class AuditTrailHandler:
    """Records response data to an in-memory audit trail."""

    def __init__(self) -> None:
        self._audit_log: list[dict[str, Any]] = []

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "auditTrail"

    def get_handler(self, constraint: Any) -> Callable[[Any], None]:
        action = constraint.get("action", "unknown")

        def handler(value: Any) -> None:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "value": value,
            }
            self._audit_log.append(entry)
            log.info("[AUDIT] %s: recorded response", action, handler="AuditTrailHandler")

        return handler

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Return a copy of the audit log for the auxiliary endpoint."""
        return list(self._audit_log)
