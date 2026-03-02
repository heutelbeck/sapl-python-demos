"""MethodInvocationConstraintHandlerProvider -- InjectTimestampHandler.

Handles obligations/advice of type "injectTimestamp".
Modifies the method invocation kwargs BEFORE the endpoint function executes,
adding a policy-enforcement timestamp. The endpoint can then read this value
and include it in the response.

Policy obligation example:
  { "type": "injectTimestamp" }
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import structlog

from sapl_base.constraint_types import MethodInvocationContext

log = structlog.get_logger()


class InjectTimestampHandler:
    """Injects a policy_timestamp into kwargs before the endpoint runs."""

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "injectTimestamp"

    def get_handler(self, constraint: Any) -> Callable[[MethodInvocationContext], None]:
        def handler(context: MethodInvocationContext) -> None:
            timestamp = datetime.now(timezone.utc).isoformat()
            context.kwargs["policy_timestamp"] = timestamp
            log.info(
                "[METHOD] Injected policy timestamp: %s",
                timestamp,
                handler="InjectTimestampHandler",
            )

        return handler
