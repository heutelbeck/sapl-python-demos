"""ErrorMappingConstraintHandlerProvider -- EnrichErrorHandler.

Handles obligations/advice of type "enrichError".
When the endpoint raises an exception, this handler TRANSFORMS the error
by wrapping it with additional context (e.g., a support URL).

This differs from ErrorHandlerProvider (side-effect only) --
ErrorMappingConstraintHandlerProvider returns a NEW error that replaces
the original.

Policy obligation example:
  { "type": "enrichError", "supportUrl": "https://support.example.com" }
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog

log = structlog.get_logger()


class EnrichErrorHandler:
    """Transforms errors by appending a support URL."""

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "enrichError"

    def get_priority(self) -> int:
        return 0

    def get_handler(self, constraint: Any) -> Callable[[Exception], Exception]:
        support_url = constraint.get("supportUrl", "https://support.example.com")

        def handler(error: Exception) -> Exception:
            log.info(
                "[ERROR-ENRICH] Enriching error with support URL: %s",
                support_url,
                handler="EnrichErrorHandler",
            )
            enriched = type(error)(f"{error} | Support: {support_url}")
            enriched.__cause__ = error
            return enriched

        return handler
