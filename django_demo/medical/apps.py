"""Django app configuration for the medical demo application.

Registers all custom SAPL constraint handler providers on startup.
"""
from __future__ import annotations

import structlog
from django.apps import AppConfig

log = structlog.get_logger()


class MedicalConfig(AppConfig):
    """Medical demo app: registers SAPL providers on `ready()`."""

    name = "medical"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from sapl_django.config import register_provider

        from medical.handlers.audit_trail import AuditTrailHandler
        from medical.handlers.cap_transfer import CapTransferHandler
        from medical.handlers.classification_filter import ClassificationFilterHandler
        from medical.handlers.enrich_error import EnrichErrorHandler
        from medical.handlers.inject_timestamp import InjectTimestampHandler
        from medical.handlers.log_access import LogAccessHandler
        from medical.handlers.log_stream_event import LogStreamEventHandler
        from medical.handlers.notify_on_error import NotifyOnErrorHandler
        from medical.handlers.redact_fields import RedactFieldsHandler

        import medical.handlers as handlers_pkg
        handlers_pkg.audit_trail_handler = AuditTrailHandler()

        register_provider(LogAccessHandler())
        register_provider(handlers_pkg.audit_trail_handler)
        register_provider(RedactFieldsHandler())
        register_provider(ClassificationFilterHandler())
        register_provider(InjectTimestampHandler())
        register_provider(CapTransferHandler())
        register_provider(NotifyOnErrorHandler())
        register_provider(LogStreamEventHandler())
        register_provider(EnrichErrorHandler())

        log.info("SAPL configured with all constraint handlers registered")
