"""MappingConstraintHandlerProvider -- RedactFieldsHandler.

Handles obligations/advice of type "redactFields".
Transforms the response by replacing specified fields with "[REDACTED]".
Unlike the built-in ContentFilter (which handles blacken/delete/replace
via filterJsonContent), this is a custom domain-specific transformation.

Policy obligation example:
  { "type": "redactFields", "fields": ["ssn", "creditCard"] }
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog

log = structlog.get_logger()


class RedactFieldsHandler:
    """Replaces specified fields with '[REDACTED]' in the response."""

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "redactFields"

    def get_priority(self) -> int:
        return 0

    def get_handler(self, constraint: Any) -> Callable[[Any], Any]:
        fields: list[str] = constraint.get("fields", [])

        def handler(value: Any) -> Any:
            if value is None or not isinstance(value, dict):
                return value
            copy = dict(value)
            for field in fields:
                if field in copy:
                    log.info("[REDACT] Redacting field: %s", field, handler="RedactFieldsHandler")
                    copy[field] = "[REDACTED]"
            return copy

        return handler
