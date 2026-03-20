"""Constraint handler providers for SAPL FastMCP demo."""

import copy
import logging
from collections.abc import Callable
from typing import Any

from sapl_base.constraint_types import MethodInvocationContext, Signal

BLACKEN_CHAR = "X"

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


class RedactFieldsProvider:
    """Redacts named fields anywhere in the return value.

    Walks dicts and lists recursively. When a dict key matches one of
    the configured field names, the value is blackened, replaced, or
    deleted depending on the mode.

    Handles obligations like:
        {"type": "redactFields", "fields": ["email", "card_number"],
         "mode": "blacken", "discloseRight": 4}

    Modes:
        blacken  - replace characters with X, optionally disclose left/right
        replace  - swap value with a fixed string (default "REDACTED")
        delete   - remove the key entirely
    """

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "redactFields"

    def get_priority(self) -> int:
        return 0

    def get_handler(self, constraint: Any) -> Callable[[Any], Any]:
        fields = set(constraint.get("fields", []))
        mode = constraint.get("mode", "blacken")
        replacement = constraint.get("replacement", "REDACTED")
        disclose_left = int(constraint.get("discloseLeft", 0))
        disclose_right = int(constraint.get("discloseRight", 0))

        def blacken(value: str) -> str:
            length = len(value)
            if disclose_left + disclose_right >= length:
                return value
            left = value[:disclose_left]
            right = value[length - disclose_right:] if disclose_right > 0 else ""
            middle = BLACKEN_CHAR * (length - disclose_left - disclose_right)
            return left + middle + right

        def redact_value(value: Any) -> Any:
            if mode == "blacken" and isinstance(value, str):
                return blacken(value)
            if mode == "replace":
                return replacement
            return value

        def walk(obj: Any) -> Any:
            if isinstance(obj, dict):
                result = {}
                for key, value in obj.items():
                    if key in fields:
                        if mode == "delete":
                            continue
                        result[key] = redact_value(value)
                    else:
                        result[key] = walk(value)
                return result
            if isinstance(obj, list):
                return [walk(element) for element in obj]
            return obj

        def handler(value: Any) -> Any:
            return walk(copy.deepcopy(value))

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
