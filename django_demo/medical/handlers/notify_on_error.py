"""ErrorHandlerProvider -- NotifyOnErrorHandler.

Handles obligations/advice of type "notifyOnError".
When the endpoint raises an exception, this handler runs a side-effect
(logging/notification) WITHOUT modifying the error.

In production, this could send alerts to monitoring systems, record the
error in an audit log, or notify on-call staff.

Policy obligation example:
  { "type": "notifyOnError" }
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog

log = structlog.get_logger()


class NotifyOnErrorHandler:
    """Logs errors from policy-protected operations as a side effect."""

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "notifyOnError"

    def get_handler(self, constraint: Any) -> Callable[[Exception], None]:
        def handler(error: Exception) -> None:
            log.warning(
                "[ERROR-NOTIFY] Error during policy-protected operation: %s",
                str(error),
                handler="NotifyOnErrorHandler",
            )

        return handler
