"""Django app configuration for the medical demo application.

Registers all 7 SAPL constraint handler types on startup so they are
available for policy enforcement across all views.
"""
from __future__ import annotations

import structlog
from django.apps import AppConfig

log = structlog.get_logger()


class MedicalConfig(AppConfig):
    """Medical demo app -- registers SAPL constraint handlers on ready()."""

    name = "medical"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        """Register all constraint handlers with the SAPL enforcement service."""
        from sapl_django.config import register_constraint_handler

        from medical.handlers.audit_trail import AuditTrailHandler
        from medical.handlers.cap_transfer import CapTransferHandler
        from medical.handlers.classification_filter import ClassificationFilterHandler
        from medical.handlers.enrich_error import EnrichErrorHandler
        from medical.handlers.inject_timestamp import InjectTimestampHandler
        from medical.handlers.log_access import LogAccessHandler
        from medical.handlers.log_stream_event import LogStreamEventHandler
        from medical.handlers.notify_on_error import NotifyOnErrorHandler
        from medical.handlers.redact_fields import RedactFieldsHandler

        # Store audit trail handler at module level for the audit-log endpoint
        import medical.handlers as handlers_pkg
        handlers_pkg.audit_trail_handler = AuditTrailHandler()

        # 1. RunnableConstraintHandlerProvider (ON_DECISION)
        register_constraint_handler(LogAccessHandler(), "runnable")

        # 2. ConsumerConstraintHandlerProvider
        register_constraint_handler(handlers_pkg.audit_trail_handler, "consumer")

        # 3. MappingConstraintHandlerProvider
        register_constraint_handler(RedactFieldsHandler(), "mapping")

        # 4. FilterPredicateConstraintHandlerProvider
        register_constraint_handler(ClassificationFilterHandler(), "filter_predicate")

        # 5. MethodInvocationConstraintHandlerProvider (inject timestamp)
        register_constraint_handler(InjectTimestampHandler(), "method_invocation")

        # 5b. MethodInvocationConstraintHandlerProvider (cap transfer amount)
        register_constraint_handler(CapTransferHandler(), "method_invocation")

        # 6. ErrorHandlerProvider
        register_constraint_handler(NotifyOnErrorHandler(), "error_handler")

        # 7. ErrorMappingConstraintHandlerProvider
        register_constraint_handler(EnrichErrorHandler(), "error_mapping")

        # 8. ConsumerConstraintHandlerProvider (streaming log)
        register_constraint_handler(LogStreamEventHandler(), "consumer")

        log.info("SAPL configured with all constraint handlers registered")
