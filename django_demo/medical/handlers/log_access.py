"""RunnableConstraintHandlerProvider -- LogAccessHandler.

Handles obligations/advice of type "logAccess".
Runs a side-effect (logging) when a PDP decision is received,
BEFORE the controller method executes.

Policy obligation example:
  { "type": "logAccess", "message": "Patient data accessed by clinician" }
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog

from sapl_base.constraint_types import Signal

log = structlog.get_logger()


class LogAccessHandler:
    """Logs a policy-defined message on each authorization decision."""

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "logAccess"

    def get_signal(self) -> Signal:
        return Signal.ON_DECISION

    def get_handler(self, constraint: Any) -> Callable[[], None]:
        message = constraint.get("message", "Access logged")

        def handler() -> None:
            log.info("[POLICY] %s", message, handler="LogAccessHandler")

        return handler
