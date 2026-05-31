"""AuditTrailHandler: OUTPUT consumer for `auditTrail` obligations."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

import structlog

from sapl_base.pep import OUTPUT, ScopedHandler

log = structlog.get_logger()


class AuditTrailHandler:
    """Records each response into an in-memory audit log."""

    def __init__(self) -> None:
        self._audit_log: list[dict[str, Any]] = []

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "auditTrail":
            return ()
        action = constraint.get("action", "unknown")

        def handler(value: Any) -> None:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "value": value,
            }
            self._audit_log.append(entry)
            log.info("[AUDIT] %s: recorded response", action, handler="AuditTrailHandler")

        return (ScopedHandler(signal=OUTPUT, priority=25, shape="consumer", handler=handler),)

    def get_audit_log(self) -> list[dict[str, Any]]:
        return list(self._audit_log)
