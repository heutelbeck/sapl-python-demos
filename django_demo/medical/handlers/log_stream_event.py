"""ConsumerConstraintHandlerProvider -- LogStreamEventHandler.

Handles obligations/advice of type "logStreamEvent".
Logs each streaming value as a side-effect without modifying it.
Used in streaming enforcement contexts.

Policy obligation example:
  { "type": "logStreamEvent", "message": "Heartbeat received" }
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog

log = structlog.get_logger()


class LogStreamEventHandler:
    """Logs streaming events as a side-effect."""

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "logStreamEvent"

    def get_handler(self, constraint: Any) -> Callable[[Any], None]:
        message = constraint.get("message", "Stream event")

        def handler(value: Any) -> None:
            log.info("[STREAM-LOG] %s: %s", message, value, handler="LogStreamEventHandler")

        return handler
