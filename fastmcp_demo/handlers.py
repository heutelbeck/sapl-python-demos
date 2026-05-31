"""Constraint handler providers for the SAPL FastMCP demo.

Each provider implements ``ConstraintHandlerProvider.get_handlers(constraint)``
and returns ``ScopedHandler`` instances at the appropriate signals:

  * AccessLoggingProvider          -> DECISION runner
  * LimitResultsProvider           -> INPUT    mapper
  * RedactFieldsProvider           -> OUTPUT   mapper
  * FilterByClassificationProvider -> OUTPUT   mapper (walks list, drops elements)
"""

from __future__ import annotations

import copy
import logging
from collections.abc import Sequence
from typing import Any

from sapl_base.pep import DECISION, INPUT, OUTPUT, ScopedHandler

BLACKEN_CHAR = "X"

logger = logging.getLogger("sapl.mcp")


class AccessLoggingProvider:
    """DECISION runner: logs tool access. Handles ``logAccess`` obligations."""

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "logAccess":
            return ()
        message = constraint.get("message", "Tool access")
        subject = constraint.get("subject", "unknown")
        action = constraint.get("action", "unknown")

        def handler() -> None:
            logger.info(
                "ACCESS LOG: %s -- subject=%s, action=%s", message, subject, action
            )

        return (ScopedHandler(signal=DECISION, priority=0, shape="runner", handler=handler),)


class LimitResultsProvider:
    """INPUT mapper: caps the ``limit`` argument based on a policy obligation.

    Handles obligations like ``{"type": "limitResults", "maxLimit": 5}``.
    If the caller's ``limit`` exceeds ``maxLimit``, it is clamped down.
    """

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "limitResults":
            return ()
        max_limit = int(constraint.get("maxLimit", 10))

        def handler(value: Any) -> Any:
            args, kwargs = value
            kwargs = dict(kwargs)
            current = kwargs.get("limit")
            if current is None:
                return (args, kwargs)
            try:
                current_int = int(current)
            except (TypeError, ValueError):
                kwargs["limit"] = max_limit
                return (args, kwargs)
            if current_int > max_limit:
                kwargs["limit"] = max_limit
            return (args, kwargs)

        return (ScopedHandler(signal=INPUT, priority=0, shape="mapper", handler=handler),)


class RedactFieldsProvider:
    """OUTPUT mapper: redacts named fields anywhere in the return value.

    Walks dicts and lists recursively. When a dict key matches one of
    the configured field names, the value is blackened, replaced, or
    deleted depending on the mode.

    Handles obligations like::

        {"type": "redactFields", "fields": ["email", "card_number"],
         "mode": "blacken", "discloseRight": 4}

    Modes:
        blacken  - replace characters with X, optionally disclose left/right
        replace  - swap value with a fixed string (default "REDACTED")
        delete   - remove the key entirely
    """

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "redactFields":
            return ()
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

        return (ScopedHandler(signal=OUTPUT, priority=10, shape="mapper", handler=handler),)


class FilterByClassificationProvider:
    """OUTPUT mapper: filters list results by classification level.

    Handles obligations like::

        {"type": "filterByClassification", "allowedLevels": ["public", "internal"]}

    When the return value is a list, removes elements whose
    ``classification`` field is not in the allowed set. Non-list return
    values pass through unchanged. Non-dict elements pass through.
    """

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "filterByClassification":
            return ()
        allowed = set(constraint.get("allowedLevels", []))

        def handler(value: Any) -> Any:
            if not isinstance(value, list):
                return value
            return [
                element
                for element in value
                if not isinstance(element, dict)
                or element.get("classification") in allowed
            ]

        return (ScopedHandler(signal=OUTPUT, priority=20, shape="mapper", handler=handler),)
