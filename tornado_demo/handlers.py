"""Constraint handler implementations for the Tornado SAPL demo.

Demonstrates all 7 constraint handler types:
  1. RunnableConstraintHandlerProvider (LogAccessHandler)
  2. ConsumerConstraintHandlerProvider (AuditTrailHandler)
  3. MappingConstraintHandlerProvider (RedactFieldsHandler)
  4. FilterPredicateConstraintHandlerProvider (ClassificationFilterHandler)
  5. MethodInvocationConstraintHandlerProvider (InjectTimestampHandler, CapTransferHandler)
  6. ErrorHandlerProvider (NotifyOnErrorHandler)
  7. ErrorMappingConstraintHandlerProvider (EnrichErrorHandler)
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import structlog

from sapl_base.constraint_types import MethodInvocationContext, Signal
from sapl_tornado.dependencies import register_constraint_handler

log = structlog.get_logger()

_CLASSIFICATION_LEVELS: dict[str, int] = {
    "PUBLIC": 0,
    "INTERNAL": 1,
    "CONFIDENTIAL": 2,
    "SECRET": 3,
}


class LogAccessHandler:
    """RunnableConstraintHandlerProvider -- logs a policy-defined message on each decision."""

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "logAccess"

    def get_signal(self) -> Signal:
        return Signal.ON_DECISION

    def get_handler(self, constraint: Any) -> Callable[[], None]:
        message = constraint.get("message", "Access logged")

        def handler() -> None:
            log.info("[POLICY] %s", message, handler="LogAccessHandler")

        return handler


class AuditTrailHandler:
    """ConsumerConstraintHandlerProvider -- records response data to an in-memory audit trail."""

    def __init__(self) -> None:
        self._audit_log: list[dict[str, Any]] = []

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "auditTrail"

    def get_handler(self, constraint: Any) -> Callable[[Any], None]:
        action = constraint.get("action", "unknown")

        def handler(value: Any) -> None:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "value": value,
            }
            self._audit_log.append(entry)
            log.info("[AUDIT] %s: recorded response", action, handler="AuditTrailHandler")

        return handler

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Return a copy of the audit log for the auxiliary endpoint."""
        return list(self._audit_log)


class RedactFieldsHandler:
    """MappingConstraintHandlerProvider -- replaces specified fields with '[REDACTED]'."""

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
            for field_name in fields:
                if field_name in copy:
                    log.info("[REDACT] Redacting field: %s", field_name, handler="RedactFieldsHandler")
                    copy[field_name] = "[REDACTED]"
            return copy

        return handler


class ClassificationFilterHandler:
    """FilterPredicateConstraintHandlerProvider -- filters list elements by classification level."""

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "filterByClassification"

    def get_handler(self, constraint: Any) -> Callable[[Any], bool]:
        max_level = constraint.get("maxLevel", "PUBLIC")
        max_rank = _CLASSIFICATION_LEVELS.get(max_level, 0)

        def predicate(element: Any) -> bool:
            if not isinstance(element, dict):
                return False
            element_level = element.get("classification")
            element_rank = _CLASSIFICATION_LEVELS.get(element_level)
            if element_rank is None:
                log.warning(
                    "[FILTER] Element excluded: unknown classification",
                    classification=element_level,
                    handler="ClassificationFilterHandler",
                )
                return False
            allowed = element_rank <= max_rank
            if not allowed:
                log.info(
                    "[FILTER] Excluded %s element (max: %s)",
                    element_level,
                    max_level,
                    handler="ClassificationFilterHandler",
                )
            return allowed

        return predicate


class InjectTimestampHandler:
    """MethodInvocationConstraintHandlerProvider -- injects a policy_timestamp into kwargs."""

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


class CapTransferHandler:
    """MethodInvocationConstraintHandlerProvider -- caps a numeric argument at a policy-defined maximum."""

    _PARAM_NAME = "amount"

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "capTransferAmount"

    def get_handler(self, constraint: Any) -> Callable[[MethodInvocationContext], None]:
        max_amount = constraint.get("maxAmount", 0)

        def handler(context: MethodInvocationContext) -> None:
            if CapTransferHandler._PARAM_NAME in context.kwargs:
                requested = float(context.kwargs[CapTransferHandler._PARAM_NAME])
                if requested > max_amount:
                    context.kwargs[CapTransferHandler._PARAM_NAME] = max_amount
                    log.info(
                        "Amount capped by policy",
                        handler="CapTransferHandler",
                        function=context.function_name,
                        requested=requested,
                        capped_to=max_amount,
                    )
                return
            for i, arg in enumerate(context.args):
                if isinstance(arg, (int, float)) and arg > max_amount:
                    context.args[i] = max_amount
                    log.info(
                        "Amount capped by policy",
                        handler="CapTransferHandler",
                        function=context.function_name,
                        requested=arg,
                        capped_to=max_amount,
                    )
                    return

        return handler


class NotifyOnErrorHandler:
    """ErrorHandlerProvider -- logs errors from policy-protected operations as a side effect."""

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


class LogStreamEventHandler:
    """ConsumerConstraintHandlerProvider -- logs streaming events as a side-effect."""

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "logStreamEvent"

    def get_handler(self, constraint: Any) -> Callable[[Any], None]:
        message = constraint.get("message", "Stream event")

        def handler(value: Any) -> None:
            log.info("[STREAM-LOG] %s: %s", message, value, handler="LogStreamEventHandler")

        return handler


class EnrichErrorHandler:
    """ErrorMappingConstraintHandlerProvider -- transforms errors by appending a support URL."""

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


# Module-level instance so the audit-log endpoint can access it
audit_trail_handler = AuditTrailHandler()


def register_all_handlers() -> None:
    """Register all constraint handlers with SAPL."""
    register_constraint_handler(LogAccessHandler(), "runnable")
    register_constraint_handler(audit_trail_handler, "consumer")
    register_constraint_handler(RedactFieldsHandler(), "mapping")
    register_constraint_handler(ClassificationFilterHandler(), "filter_predicate")
    register_constraint_handler(InjectTimestampHandler(), "method_invocation")
    register_constraint_handler(CapTransferHandler(), "method_invocation")
    register_constraint_handler(NotifyOnErrorHandler(), "error_handler")
    register_constraint_handler(EnrichErrorHandler(), "error_mapping")
    register_constraint_handler(LogStreamEventHandler(), "consumer")
