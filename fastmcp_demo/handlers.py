"""Constraint handler providers for SAPL FastMCP demo."""

import logging
from collections.abc import Callable
from typing import Any

from sapl_base.constraint_types import MethodInvocationContext, Signal

logger = logging.getLogger("sapl.mcp")


class AccessLoggingProvider:
    """Logs tool access. Handles obligations/advice with type 'logAccess'."""

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "logAccess"

    def get_signal(self) -> Signal:
        return Signal.ON_DECISION

    def get_handler(self, constraint: Any) -> Callable[[], None]:
        message = constraint.get("message", "Tool access")
        subject = constraint.get("subject", "unknown")
        action = constraint.get("action", "unknown")

        def handler() -> None:
            logger.info(
                "ACCESS LOG: %s -- subject=%s, action=%s", message, subject, action
            )

        return handler


class LimitResultsProvider:
    """Caps the 'limit' parameter based on a policy obligation.

    Handles obligations like: {"type": "limitResults", "maxLimit": 5}
    If the caller's ``limit`` exceeds ``maxLimit``, it is clamped down.
    """

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "limitResults"

    def get_handler(self, constraint: Any) -> Callable[[MethodInvocationContext], None]:
        max_limit = int(constraint.get("maxLimit", 10))

        def handler(context: MethodInvocationContext) -> None:
            current = context.kwargs.get("limit")
            if current is None:
                return
            try:
                current = int(current)
            except (TypeError, ValueError):
                context.kwargs["limit"] = max_limit
                return
            if current > max_limit:
                context.kwargs["limit"] = max_limit

        return handler


class FilterByClassificationProvider:
    """Filters list results by classification level.

    Handles obligations like:
    {"type": "filterByClassification", "allowedLevels": ["public", "internal"]}

    Removes list elements whose ``classification`` field is not in the
    allowed set. Non-dict elements pass through unfiltered.
    """

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "filterByClassification"

    def get_handler(self, constraint: Any) -> Callable[[Any], bool]:
        allowed = set(constraint.get("allowedLevels", []))

        def predicate(element: Any) -> bool:
            if isinstance(element, dict):
                return element.get("classification") in allowed
            return True

        return predicate
