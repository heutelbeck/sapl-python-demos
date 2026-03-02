"""Constraint handler demo endpoints.

Each endpoint is protected by a SAPL policy that attaches obligations or advice.
The ConstraintEnforcementService discovers registered handlers and builds a
ConstraintHandlerBundle that enforces all constraints.

Demonstrates all 7 constraint handler types plus content filtering, resource
replacement, and the obligation vs advice distinction.
"""

from __future__ import annotations

import json

import structlog
import tornado.web

from sapl_base.types import AuthorizationDecision
from sapl_tornado.decorators import post_enforce, pre_enforce

from models import DOCUMENTS

log = structlog.get_logger()


class LoggedHandler(tornado.web.RequestHandler):
    """RunnableConstraintHandlerProvider -- LogAccessHandler."""

    @pre_enforce(action="readLogged", resource="logged")
    async def get(self):
        return {
            "message": "This response was logged by a policy obligation",
            "data": {"patientId": "P-001", "status": "active"},
        }


class AuditedHandler(tornado.web.RequestHandler):
    """ConsumerConstraintHandlerProvider -- AuditTrailHandler."""

    @pre_enforce(action="readAudited", resource="audited")
    async def get(self):
        return {
            "message": "This response was recorded in the audit trail",
            "record": {"id": "MR-42", "type": "blood-work", "result": "normal"},
        }


class AuditLogHandler(tornado.web.RequestHandler):
    """Auxiliary endpoint: view the in-memory audit trail."""

    def get(self):
        from handlers import audit_trail_handler

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(audit_trail_handler.get_audit_log()))


class RedactedHandler(tornado.web.RequestHandler):
    """MappingConstraintHandlerProvider -- RedactFieldsHandler."""

    @pre_enforce(action="readRedacted", resource="redacted")
    async def get(self):
        return {
            "name": "John Smith",
            "ssn": "987-65-4321",
            "creditCard": "4111-1111-1111-1111",
            "email": "john@example.com",
            "balance": 1500.0,
        }


class ConstraintPatientHandler(tornado.web.RequestHandler):
    """Content Filter -- blacken."""

    @pre_enforce(action="readPatient", resource="patient")
    async def get(self):
        return {
            "name": "Jane Doe",
            "ssn": "123-45-6789",
            "email": "jane.doe@example.com",
            "diagnosis": "healthy",
        }


class PatientFullHandler(tornado.web.RequestHandler):
    """Content Filter -- blacken + delete + replace (all three actions)."""

    @pre_enforce(action="readPatientFull", resource="patientFull")
    async def get(self):
        return {
            "name": "Jane Doe",
            "ssn": "123-45-6789",
            "email": "jane.doe@example.com",
            "diagnosis": "healthy",
            "internal_notes": "Follow-up scheduled for next week",
        }


class DocumentsHandler(tornado.web.RequestHandler):
    """FilterPredicateConstraintHandlerProvider -- ClassificationFilterHandler."""

    @pre_enforce(action="readDocuments", resource="documents")
    async def get(self):
        return [dict(d) for d in DOCUMENTS]


class TimestampedHandler(tornado.web.RequestHandler):
    """MethodInvocationConstraintHandlerProvider -- InjectTimestampHandler."""

    @pre_enforce(action="readTimestamped", resource="timestamped")
    async def get(self, policy_timestamp="not injected"):
        return {
            "message": "This response includes a policy-injected timestamp",
            "policy_timestamp": policy_timestamp,
            "data": {"sensor": "temp-01", "value": 22.5},
        }


class ErrorDemoHandler(tornado.web.RequestHandler):
    """ErrorHandlerProvider + ErrorMappingConstraintHandlerProvider."""

    @pre_enforce(action="readErrorDemo", resource="errorDemo")
    async def get(self):
        raise RuntimeError("Simulated backend failure")

    def write_error(self, status_code, **kwargs):
        if "exc_info" in kwargs:
            exc = kwargs["exc_info"][1]
            if isinstance(exc, RuntimeError):
                self.set_header("Content-Type", "application/json; charset=UTF-8")
                self.set_status(500)
                self.write(json.dumps({"error": str(exc)}))
                return
        super().write_error(status_code, **kwargs)


class ResourceReplacedHandler(tornado.web.RequestHandler):
    """Resource Replacement."""

    @pre_enforce(action="readReplaced", resource="replaced")
    async def get(self):
        return {
            "message": "You should NOT see this -- the PDP replaces this resource",
            "originalData": True,
        }


class AdvisedHandler(tornado.web.RequestHandler):
    """Advice vs Obligations."""

    @pre_enforce(action="readAdvised", resource="advised")
    async def get(self):
        return {
            "message": "Access granted despite unhandled advice",
            "data": {"category": "medical", "status": "reviewed"},
        }


class RecordHandler(tornado.web.RequestHandler):
    """PostEnforce with return value in subscription."""

    @post_enforce(
        action="readRecord",
        resource=lambda ctx: {"type": "record", "data": ctx.return_value},
    )
    async def get(self, record_id):
        log.info("Fetching record", record_id=record_id)
        return {"id": record_id, "value": "sensitive-data", "classification": "confidential"}


class UnhandledHandler(tornado.web.RequestHandler):
    """Unhandled Obligation -- Fail-Fast."""

    @pre_enforce(action="readSecret", resource="secret")
    async def get(self):
        return {"data": "you should not see this"}


def _handle_audit_deny(decision: AuthorizationDecision):
    """Custom deny handler for audit endpoint."""
    return {"denied": True, "reason": decision.decision.value}


class AuditHandler(tornado.web.RequestHandler):
    """PostEnforce with onDeny callback."""

    @post_enforce(action="readAudit", resource="audit", on_deny=_handle_audit_deny)
    async def get(self):
        return {
            "entries": [{"action": "login", "timestamp": "2026-01-01T00:00:00Z"}],
        }


ConstraintHandlers = [
    (r"/api/constraints/logged", LoggedHandler),
    (r"/api/constraints/audited", AuditedHandler),
    (r"/api/constraints/audit-log", AuditLogHandler),
    (r"/api/constraints/redacted", RedactedHandler),
    (r"/api/constraints/patient", ConstraintPatientHandler),
    (r"/api/constraints/patient-full", PatientFullHandler),
    (r"/api/constraints/documents", DocumentsHandler),
    (r"/api/constraints/timestamped", TimestampedHandler),
    (r"/api/constraints/error-demo", ErrorDemoHandler),
    (r"/api/constraints/resource-replaced", ResourceReplacedHandler),
    (r"/api/constraints/advised", AdvisedHandler),
    (r"/api/constraints/record/(?P<record_id>[^/]+)", RecordHandler),
    (r"/api/constraints/unhandled", UnhandledHandler),
    (r"/api/constraints/audit", AuditHandler),
]
