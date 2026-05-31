"""Constraint handler implementations for the Flask SAPL demo.

Each class implements `ConstraintHandlerProvider.get_handlers(constraint)` and
returns one `ScopedHandler` at the appropriate signal:

  * LogAccessHandler           -> DECISION runner
  * AuditTrailHandler          -> OUTPUT  consumer
  * RedactFieldsHandler        -> OUTPUT  mapper  (priority 5)
  * ClassificationFilterHandler-> OUTPUT  mapper  (priority 10)
  * LogStreamEventHandler      -> OUTPUT  consumer
  * InjectTimestampHandler     -> INPUT   mapper  (priority 0)
  * CapTransferHandler         -> INPUT   mapper  (priority 10)
  * NotifyOnErrorHandler       -> ERROR   consumer
  * EnrichErrorHandler         -> ERROR   mapper

`SubscriptionContext`, `args`/`kwargs` plumbing is handled by `sapl_base.pep`
internally: INPUT mappers receive `(args, kwargs)` tuples and return new ones;
OUTPUT mappers receive a value and return a transformed value; ERROR
mappers receive an exception and return a (possibly wrapped) exception.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

import structlog

from sapl_base.pep import DECISION, ERROR, INPUT, OUTPUT, ScopedHandler

from sapl_flask.extension import SaplFlask

log = structlog.get_logger()

_CLASSIFICATION_LEVELS: dict[str, int] = {
    "PUBLIC": 0,
    "INTERNAL": 1,
    "CONFIDENTIAL": 2,
    "SECRET": 3,
}


class LogAccessHandler:
    """DECISION runner: logs a policy-defined message on each decision."""

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "logAccess":
            return ()
        message = constraint.get("message", "Access logged")

        def handler() -> None:
            log.info("[POLICY] %s", message, handler="LogAccessHandler")

        return (ScopedHandler(signal=DECISION, priority=0, shape="runner", handler=handler),)


class AuditTrailHandler:
    """OUTPUT consumer: records each response to an in-memory audit log."""

    def __init__(self) -> None:
        self._audit_log: list[dict[str, Any]] = []

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "auditTrail":
            return ()
        action = constraint.get("action", "unknown")

        def handler(value: Any) -> None:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "value": value,
            }
            self._audit_log.append(entry)
            log.info("[AUDIT] %s: recorded response", action, handler="AuditTrailHandler")

        return (ScopedHandler(signal=OUTPUT, priority=25, shape="consumer", handler=handler),)

    def get_audit_log(self) -> list[dict[str, Any]]:
        return list(self._audit_log)


class RedactFieldsHandler:
    """OUTPUT mapper: replaces specified fields with '[REDACTED]'."""

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "redactFields":
            return ()
        fields: list[str] = constraint.get("fields", [])

        def handler(value: Any) -> Any:
            if not isinstance(value, dict):
                return value
            copy = dict(value)
            for field_name in fields:
                if field_name in copy:
                    log.info("[REDACT] Redacting field: %s", field_name, handler="RedactFieldsHandler")
                    copy[field_name] = "[REDACTED]"
            return copy

        return (ScopedHandler(signal=OUTPUT, priority=5, shape="mapper", handler=handler),)


class ClassificationFilterHandler:
    """OUTPUT mapper: filters list elements by classification level."""

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "filterByClassification":
            return ()
        max_level = constraint.get("maxLevel", "PUBLIC")
        max_rank = _CLASSIFICATION_LEVELS.get(max_level, 0)

        def handler(value: Any) -> Any:
            if not isinstance(value, list):
                return value
            kept: list[Any] = []
            for element in value:
                if not isinstance(element, dict):
                    continue
                element_level = element.get("classification")
                element_rank = _CLASSIFICATION_LEVELS.get(element_level)
                if element_rank is None:
                    log.warning(
                        "[FILTER] Element excluded: unknown classification",
                        classification=element_level,
                        handler="ClassificationFilterHandler",
                    )
                    continue
                if element_rank <= max_rank:
                    kept.append(element)
                else:
                    log.info(
                        "[FILTER] Excluded %s element (max: %s)",
                        element_level,
                        max_level,
                        handler="ClassificationFilterHandler",
                    )
            return kept

        return (ScopedHandler(signal=OUTPUT, priority=10, shape="mapper", handler=handler),)


class InjectTimestampHandler:
    """INPUT mapper: injects a `policy_timestamp` kwarg before view executes."""

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "injectTimestamp":
            return ()

        def handler(value: Any) -> Any:
            args, kwargs = value
            kwargs = dict(kwargs)
            timestamp = datetime.now(timezone.utc).isoformat()
            kwargs["policy_timestamp"] = timestamp
            log.info("[METHOD] Injected policy timestamp: %s", timestamp, handler="InjectTimestampHandler")
            return (args, kwargs)

        return (ScopedHandler(signal=INPUT, priority=0, shape="mapper", handler=handler),)


class CapTransferHandler:
    """INPUT mapper: caps a numeric argument at a policy-defined maximum."""

    _PARAM_NAME = "amount"

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "capTransferAmount":
            return ()
        max_amount = constraint.get("maxAmount", 0)

        def handler(value: Any) -> Any:
            args, kwargs = value
            kwargs = dict(kwargs)
            args = list(args)
            if CapTransferHandler._PARAM_NAME in kwargs:
                requested = float(kwargs[CapTransferHandler._PARAM_NAME])
                if requested > max_amount:
                    kwargs[CapTransferHandler._PARAM_NAME] = max_amount
                    log.info(
                        "Amount capped by policy",
                        handler="CapTransferHandler",
                        requested=requested,
                        capped_to=max_amount,
                    )
                return (tuple(args), kwargs)
            for i, arg in enumerate(args):
                if isinstance(arg, (int, float)) and arg > max_amount:
                    args[i] = max_amount
                    log.info(
                        "Amount capped by policy",
                        handler="CapTransferHandler",
                        requested=arg,
                        capped_to=max_amount,
                    )
                    break
            return (tuple(args), kwargs)

        return (ScopedHandler(signal=INPUT, priority=10, shape="mapper", handler=handler),)


class NotifyOnErrorHandler:
    """ERROR consumer: logs errors from policy-protected operations."""

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "notifyOnError":
            return ()

        def handler(error: BaseException) -> None:
            log.warning(
                "[ERROR-NOTIFY] Error during policy-protected operation: %s",
                str(error),
                handler="NotifyOnErrorHandler",
            )

        return (ScopedHandler(signal=ERROR, priority=0, shape="consumer", handler=handler),)


class LogStreamEventHandler:
    """OUTPUT consumer: logs streaming events as a side-effect."""

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "logStreamEvent":
            return ()
        message = constraint.get("message", "Stream event")

        def handler(value: Any) -> None:
            log.info("[STREAM-LOG] %s: %s", message, value, handler="LogStreamEventHandler")

        return (ScopedHandler(signal=OUTPUT, priority=30, shape="consumer", handler=handler),)


class EnrichErrorHandler:
    """ERROR mapper: transforms errors by appending a support URL."""

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "enrichError":
            return ()
        support_url = constraint.get("supportUrl", "https://support.example.com")

        def handler(error: BaseException) -> BaseException:
            log.info(
                "[ERROR-ENRICH] Enriching error with support URL: %s",
                support_url,
                handler="EnrichErrorHandler",
            )
            enriched: BaseException = type(error)(f"{error} | Support: {support_url}")
            enriched.__cause__ = error
            return enriched

        return (ScopedHandler(signal=ERROR, priority=0, shape="mapper", handler=handler),)


audit_trail_handler = AuditTrailHandler()


def register_all_handlers(sapl: SaplFlask) -> None:
    """Register every custom constraint handler provider with the extension."""
    sapl.register_provider(LogAccessHandler())
    sapl.register_provider(audit_trail_handler)
    sapl.register_provider(RedactFieldsHandler())
    sapl.register_provider(ClassificationFilterHandler())
    sapl.register_provider(InjectTimestampHandler())
    sapl.register_provider(CapTransferHandler())
    sapl.register_provider(NotifyOnErrorHandler())
    sapl.register_provider(LogStreamEventHandler())
    sapl.register_provider(EnrichErrorHandler())
