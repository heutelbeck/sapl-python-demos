"""RedactFieldsHandler: OUTPUT mapper for `redactFields` obligations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import structlog

from sapl_base.pep import OUTPUT, ScopedHandler

log = structlog.get_logger()


class RedactFieldsHandler:
    """Replaces specified fields with '[REDACTED]' in the response."""

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "redactFields":
            return ()
        fields: list[str] = constraint.get("fields", [])

        def handler(value: Any) -> Any:
            if not isinstance(value, dict):
                return value
            copy = dict(value)
            for field_name in fields:
                if field_name in copy:
                    log.info("[REDACT] Redacting field: %s", field_name, handler="RedactFieldsHandler")
                    copy[field_name] = "[REDACTED]"
            return copy

        return (ScopedHandler(signal=OUTPUT, priority=5, shape="mapper", handler=handler),)
