"""Constraint handler demo endpoints.

Each endpoint is protected by a SAPL policy that attaches obligations or advice.
The ConstraintEnforcementService discovers registered handlers and builds a
ConstraintHandlerBundle that enforces all constraints.

Demonstrates all 7 constraint handler types plus content filtering, resource
replacement, and the obligation vs advice distinction.
"""

from __future__ import annotations

import structlog
from flask import Blueprint, abort, jsonify

from sapl_base.types import AuthorizationDecision
from sapl_flask.decorators import pre_enforce, post_enforce

from models import DOCUMENTS

log = structlog.get_logger()

constraints_bp = Blueprint("constraints", __name__)


@constraints_bp.errorhandler(RuntimeError)
def handle_runtime_error(exc):
    """Convert RuntimeError to 500 with the error message in the response body."""
    return jsonify({"error": str(exc)}), 500


@constraints_bp.route("/logged")
@pre_enforce(action="readLogged", resource="logged")
def get_logged():
    """RunnableConstraintHandlerProvider -- LogAccessHandler.

    The PDP returns PERMIT with obligation:
      { "type": "logAccess", "message": "Patient data accessed by clinician" }

    Watch the server console for the log message.
    """
    return {
        "message": "This response was logged by a policy obligation",
        "data": {"patientId": "P-001", "status": "active"},
    }


@constraints_bp.route("/audited")
@pre_enforce(action="readAudited", resource="audited")
def get_audited():
    """ConsumerConstraintHandlerProvider -- AuditTrailHandler.

    The PDP returns PERMIT with obligation:
      { "type": "auditTrail", "action": "readMedicalRecord" }

    The response is recorded in an in-memory audit log.
    Call GET /api/constraints/audit-log to see what was recorded.
    """
    return {
        "message": "This response was recorded in the audit trail",
        "record": {"id": "MR-42", "type": "blood-work", "result": "normal"},
    }


@constraints_bp.route("/audit-log")
def get_audit_log():
    """Auxiliary endpoint: view the in-memory audit trail.

    Not policy-protected -- just shows what the AuditTrailHandler recorded.
    """
    from handlers import audit_trail_handler

    return jsonify(audit_trail_handler.get_audit_log())


@constraints_bp.route("/redacted")
@pre_enforce(action="readRedacted", resource="redacted")
def get_redacted():
    """MappingConstraintHandlerProvider -- RedactFieldsHandler.

    The PDP returns PERMIT with obligation:
      { "type": "redactFields", "fields": ["ssn", "creditCard"] }

    Expected: ssn and creditCard become "[REDACTED]", other fields unchanged.
    """
    return {
        "name": "John Smith",
        "ssn": "987-65-4321",
        "creditCard": "4111-1111-1111-1111",
        "email": "john@example.com",
        "balance": 1500.0,
    }


@constraints_bp.route("/patient")
@pre_enforce(action="readPatient", resource="patient")
def get_constraint_patient():
    """Content Filter -- blacken.

    The PDP returns PERMIT with obligation:
      { "type": "filterJsonContent", "actions": [{ "type": "blacken", "path": "$.ssn", "discloseRight": 4 }] }

    The built-in ContentFilteringProvider masks the SSN field,
    disclosing only the last 4 characters.

    Expected: { "name": "Jane Doe", "ssn": "XXXXX6789", ... }
    """
    return {
        "name": "Jane Doe",
        "ssn": "123-45-6789",
        "email": "jane.doe@example.com",
        "diagnosis": "healthy",
    }


@constraints_bp.route("/patient-full")
@pre_enforce(action="readPatientFull", resource="patientFull")
def get_patient_full():
    """Content Filter -- blacken + delete + replace (all three actions).

    The PDP returns PERMIT with obligation combining all three filter types:
      - blacken $.ssn (mask all but last 4 digits)
      - delete $.internal_notes (remove field entirely)
      - replace $.email (substitute with placeholder)

    Expected: ssn masked, internal_notes absent, email replaced.
    """
    return {
        "name": "Jane Doe",
        "ssn": "123-45-6789",
        "email": "jane.doe@example.com",
        "diagnosis": "healthy",
        "internal_notes": "Follow-up scheduled for next week",
    }


@constraints_bp.route("/documents")
@pre_enforce(action="readDocuments", resource="documents")
def get_documents():
    """FilterPredicateConstraintHandlerProvider -- ClassificationFilterHandler.

    The PDP returns PERMIT with obligation:
      { "type": "filterByClassification", "maxLevel": "INTERNAL" }

    When the endpoint returns a list, the ConstraintHandlerBundle filters
    elements using the predicate. Elements with classification above
    "INTERNAL" are excluded.

    Expected: only PUBLIC and INTERNAL documents returned.
    """
    return [dict(d) for d in DOCUMENTS]


@constraints_bp.route("/timestamped")
@pre_enforce(action="readTimestamped", resource="timestamped")
def get_timestamped(policy_timestamp: str = "not injected"):
    """MethodInvocationConstraintHandlerProvider -- InjectTimestampHandler.

    The PDP returns PERMIT with obligation:
      { "type": "injectTimestamp" }

    InjectTimestampHandler adds a "policy_timestamp" kwarg BEFORE the
    endpoint executes. The endpoint reads this injected value.

    Expected: response includes policy_timestamp set by the constraint handler.
    """
    return {
        "message": "This response includes a policy-injected timestamp",
        "policy_timestamp": policy_timestamp,
        "data": {"sensor": "temp-01", "value": 22.5},
    }


@constraints_bp.route("/error-demo")
@pre_enforce(action="readErrorDemo", resource="errorDemo")
def get_error_demo():
    """ErrorHandlerProvider + ErrorMappingConstraintHandlerProvider.

    The PDP returns PERMIT with two obligations:
      { "type": "notifyOnError" }
      { "type": "enrichError", "supportUrl": "https://support.example.com/errors" }

    The endpoint intentionally throws to demonstrate the error pipeline:
    1. NotifyOnErrorHandler logs the error (side-effect)
    2. EnrichErrorHandler transforms the error, appending a support URL

    Expected: 500 with enriched error message including the support URL.
    """
    raise RuntimeError("Simulated backend failure")


@constraints_bp.route("/resource-replaced")
@pre_enforce(action="readReplaced", resource="replaced")
def get_resource_replaced():
    """Resource Replacement.

    The PDP returns PERMIT with a "resource" field in the decision:
      { decision: "PERMIT", resource: { ... } }

    The policy uses SAPL's "transform" keyword to replace the resource.
    The ConstraintHandlerBundle substitutes the endpoint's return value
    with the PDP-provided resource. The endpoint's actual return value
    is ignored.

    Expected: the response contains the PDP-generated object.
    """
    return {
        "message": "You should NOT see this -- the PDP replaces this resource",
        "originalData": True,
    }


@constraints_bp.route("/advised")
@pre_enforce(action="readAdvised", resource="advised")
def get_advised():
    """Advice vs Obligations.

    The PDP returns PERMIT with two ADVICE constraints (not obligations):
      { "type": "logAccess", "message": "Advisory: medical data accessed" }
      { "type": "nonExistentAdviceHandler", ... }

    Key difference from obligations:
    - Obligations are MANDATORY: if no handler exists, access is denied.
    - Advice is BEST-EFFORT: if no handler exists, access is still granted.

    Expected: access granted despite unhandled advice.
    """
    return {
        "message": "Access granted despite unhandled advice",
        "data": {"category": "medical", "status": "reviewed"},
    }


@constraints_bp.route("/record/<record_id>")
@post_enforce(
    action="readRecord",
    resource=lambda ctx: {"type": "record", "data": ctx.return_value},
)
def get_record(record_id: str):
    """PostEnforce with return value in subscription.

    The resource callable receives a SubscriptionContext with the return value,
    allowing the subscription to include the endpoint's result for policy decisions.
    """
    log.info("Fetching record", record_id=record_id)
    return {"id": record_id, "value": "sensitive-data", "classification": "confidential"}


@constraints_bp.route("/unhandled")
@pre_enforce(action="readSecret", resource="secret")
def get_unhandled():
    """Unhandled Obligation -- Fail-Fast.

    The PDP returns PERMIT with an obligation of type "unknownConstraintType"
    that no registered handler can process.

    Because obligations are MANDATORY, access is denied when unhandled
    obligations are detected. The endpoint never executes.

    Expected: 403 Forbidden, regardless of the PERMIT decision.
    """
    return {"data": "you should not see this"}


def _handle_audit_deny(decision: AuthorizationDecision):
    """Custom deny handler for audit endpoint."""
    return {"denied": True, "reason": decision.decision.value}


@constraints_bp.route("/audit")
@post_enforce(
    action="readAudit",
    resource="audit",
    on_deny=_handle_audit_deny,
)
def get_audit():
    """PostEnforce with onDeny callback.

    Returns audit trail entries. If denied, returns structured JSON
    instead of 403.
    """
    return {
        "entries": [{"action": "login", "timestamp": "2026-01-01T00:00:00Z"}],
    }
