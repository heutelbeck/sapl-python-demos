"""Django async views with SAPL policy enforcement.

Demonstrates all enforcement patterns and constraint handler types
using Django async views with JsonResponse. Most endpoints use the
sapl_django decorators for declarative enforcement.

All endpoints are async and return django.http.JsonResponse.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import structlog
from django.http import HttpRequest, JsonResponse

from sapl_base.types import AuthorizationDecision, AuthorizationSubscription, Decision
from sapl_django.config import get_pdp_client
from sapl_django.decorators import (
    enforce_drop_while_denied,
    enforce_recoverable_if_denied,
    enforce_till_denied,
    pre_enforce,
    post_enforce,
)

from medical.auth import get_jwt_claims
from medical.models import DOCUMENTS, PATIENTS

log = structlog.get_logger()


def _json_error(status: int, detail: Any) -> JsonResponse:
    """Build a JSON error response."""
    body = detail if isinstance(detail, dict) else {"detail": detail}
    return JsonResponse(body, status=status)


async def root(request: HttpRequest) -> JsonResponse:
    """Health check / root endpoint."""
    return JsonResponse({"status": "ok", "application": "SAPL Django Demo"})


async def get_hello(request: HttpRequest) -> JsonResponse:
    """Manual PDP access -- no decorator.

    Calls pdp_client.decide_once() directly. The application code is
    responsible for interpreting the decision and enforcing it manually.
    """
    pdp_client = get_pdp_client()

    subscription = AuthorizationSubscription(
        subject="anonymous",
        action="read",
        resource="hello",
    )
    decision = await pdp_client.decide_once(subscription)
    log.info("PDP decision", decision=decision.decision.value)

    if decision.decision == Decision.PERMIT and not decision.obligations and not decision.has_resource:
        return JsonResponse({"message": "hello"})

    return _json_error(403, "Access denied by policy")


@pre_enforce(action="readPatient", resource="patient")
async def get_patient(request: HttpRequest, patient_id: str):
    """PreEnforce with content filtering (blacken SSN)."""
    for p in PATIENTS:
        if p["id"] == patient_id:
            return dict(p)
    return {"error": "Patient not found"}


@post_enforce(action="readPatients", resource="patients")
async def get_patients(request: HttpRequest):
    """PostEnforce returning list of patients with SSN blackening."""
    return [dict(p) for p in PATIENTS]


@pre_enforce(
    action="exportData",
    resource=lambda ctx: {"pilotId": ctx.params.get("pilot_id", ""), "sequenceId": ctx.params.get("sequence_id", "")},
    secrets=lambda ctx: {"jwt": getattr(ctx.request, "sapl_token", None)} if ctx.request and getattr(ctx.request, "sapl_token", None) else None,
)
async def get_export_data(request: HttpRequest, pilot_id: str, sequence_id: str):
    """PreEnforce with ABAC (role + pilotId check via JWT).

    The policy permit-clinician-export checks:
    - JWT claim user_role == "CLINICIAN"
    - JWT claim pilotId matches the requested pilotId
    - Time gate based on sequence end dates
    """
    await get_jwt_claims(request)
    log.info("exportData", pilot_id=pilot_id, sequence_id=sequence_id)
    return {"pilotId": pilot_id, "sequenceId": sequence_id, "data": "export-payload"}


def _handle_export_deny(decision: AuthorizationDecision):
    """Custom deny handler for exportData2 -- returns structured JSON instead of 403."""
    return {
        "error": "access_denied",
        "decision": decision.decision.value,
    }


@pre_enforce(
    action="exportData",
    resource=lambda ctx: {"pilotId": ctx.params.get("pilot_id", ""), "sequenceId": ctx.params.get("sequence_id", "")},
    secrets=lambda ctx: {"jwt": getattr(ctx.request, "sapl_token", None)} if ctx.request and getattr(ctx.request, "sapl_token", None) else None,
    on_deny=_handle_export_deny,
)
async def get_export_data2(request: HttpRequest, pilot_id: str, sequence_id: str):
    """PreEnforce with onDeny callback.

    Same policy as exportData, but instead of 403 on deny, returns structured
    JSON with the decision details.
    """
    await get_jwt_claims(request)
    log.info("exportData2", pilot_id=pilot_id, sequence_id=sequence_id)
    return {"pilotId": pilot_id, "sequenceId": sequence_id, "data": "export-payload"}


async def transfer(request: HttpRequest):
    """Thin view that parses query params and delegates to the enforced function."""
    if request.method != "POST":
        return _json_error(405, "Method not allowed")
    amount = float(request.GET.get("amount", "10000"))
    recipient = request.GET.get("recipient", "default-account")
    return await _do_transfer(amount=amount, recipient=recipient)


@pre_enforce(action="transfer", resource="account")
async def _do_transfer(amount: float = 10000.0, recipient: str = "default-account"):
    """PreEnforce with argument manipulation (cap amount).

    The CapTransferHandler caps amount via MethodInvocationContext kwargs.
    """
    return {"transferred": amount, "recipient": recipient, "status": "completed"}


@pre_enforce(action="readPatient", resource="patient")
async def get_constraint_patient(request: HttpRequest):
    """Content Filter -- blacken SSN."""
    return {
        "name": "Jane Doe",
        "ssn": "123-45-6789",
        "email": "jane.doe@example.com",
        "diagnosis": "healthy",
    }


@pre_enforce(action="readPatientFull", resource="patientFull")
async def get_patient_full(request: HttpRequest):
    """Content Filter -- blacken + delete + replace (all three actions)."""
    return {
        "name": "Jane Doe",
        "ssn": "123-45-6789",
        "email": "jane.doe@example.com",
        "diagnosis": "healthy",
        "internal_notes": "Follow-up scheduled for next week",
    }


@pre_enforce(action="readLogged", resource="logged")
async def get_logged(request: HttpRequest):
    """RunnableConstraintHandlerProvider -- LogAccessHandler."""
    return {
        "message": "This response was logged by a policy obligation",
        "data": {"patientId": "P-001", "status": "active"},
    }


@pre_enforce(action="readAudited", resource="audited")
async def get_audited(request: HttpRequest):
    """ConsumerConstraintHandlerProvider -- AuditTrailHandler."""
    return {
        "message": "This response was recorded in the audit trail",
        "record": {"id": "MR-42", "type": "blood-work", "result": "normal"},
    }


async def get_audit_log(request: HttpRequest) -> JsonResponse:
    """Auxiliary endpoint: view the in-memory audit trail.

    Not policy-protected -- just shows what the AuditTrailHandler recorded.
    """
    import medical.handlers as handlers_pkg

    handler = handlers_pkg.audit_trail_handler
    if handler is None:
        return JsonResponse([], safe=False)
    return JsonResponse(handler.get_audit_log(), safe=False)


@pre_enforce(action="readRedacted", resource="redacted")
async def get_redacted(request: HttpRequest):
    """MappingConstraintHandlerProvider -- RedactFieldsHandler."""
    return {
        "name": "John Smith",
        "ssn": "987-65-4321",
        "creditCard": "4111-1111-1111-1111",
        "email": "john@example.com",
        "balance": 1500.0,
    }


@pre_enforce(action="readDocuments", resource="documents")
async def get_documents(request: HttpRequest):
    """FilterPredicateConstraintHandlerProvider -- ClassificationFilterHandler."""
    return [dict(d) for d in DOCUMENTS]


@pre_enforce(action="readTimestamped", resource="timestamped")
async def get_timestamped(request: HttpRequest, policy_timestamp: str = "not injected"):
    """MethodInvocationConstraintHandlerProvider -- InjectTimestampHandler."""
    return {
        "message": "This response includes a policy-injected timestamp",
        "policy_timestamp": policy_timestamp,
        "data": {"sensor": "temp-01", "value": 22.5},
    }


@pre_enforce(action="readErrorDemo", resource="errorDemo")
async def get_error_demo(request: HttpRequest):
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


@pre_enforce(action="readReplaced", resource="replaced")
async def get_resource_replaced(request: HttpRequest):
    """Resource Replacement -- PDP replaces the endpoint's return value."""
    return {
        "message": "You should NOT see this -- the PDP replaces this resource",
        "originalData": True,
    }


@pre_enforce(action="readAdvised", resource="advised")
async def get_advised(request: HttpRequest):
    """Advice vs Obligations -- access granted despite unhandled advice."""
    return {
        "message": "Access granted despite unhandled advice",
        "data": {"category": "medical", "status": "reviewed"},
    }


@post_enforce(
    action="readRecord",
    resource=lambda ctx: {"type": "record", "data": ctx.return_value},
)
async def get_record(request: HttpRequest, record_id: str):
    """PostEnforce with return value in subscription.

    The resource callable receives a SubscriptionContext with the return value,
    allowing the subscription to include the endpoint's result for policy decisions.
    """
    log.info("Fetching record", record_id=record_id)
    return {"id": record_id, "value": "sensitive-data", "classification": "confidential"}


@pre_enforce(action="readSecret", resource="secret")
async def get_unhandled(request: HttpRequest):
    """Unhandled Obligation -- Fail-Fast.

    The PDP returns PERMIT with an unknown obligation type.
    Because obligations are mandatory, access is denied.
    """
    return {"data": "you should not see this"}


def _handle_audit_deny(decision: AuthorizationDecision):
    """Custom deny handler for audit endpoint."""
    return {"denied": True, "reason": decision.decision.value}


@post_enforce(
    action="readAudit",
    resource="audit",
    on_deny=_handle_audit_deny,
)
async def get_audit(request: HttpRequest):
    """PostEnforce with onDeny callback.

    Returns audit trail entries. If denied, returns structured JSON
    instead of 403.
    """
    return {
        "entries": [{"action": "login", "timestamp": "2026-01-01T00:00:00Z"}],
    }


async def _heartbeat_source():
    """Infinite heartbeat generator emitting every 2 seconds."""
    seq = 0
    while True:
        yield {"seq": seq, "ts": datetime.now(timezone.utc).isoformat()}
        seq += 1
        await asyncio.sleep(2)


def _on_deny(decision: AuthorizationDecision) -> dict[str, Any]:
    return {"type": "ACCESS_DENIED", "message": "Stream terminated by policy"}


def _on_suspend(decision: AuthorizationDecision) -> dict[str, Any]:
    return {"type": "ACCESS_SUSPENDED", "message": "Waiting for re-authorization"}


def _on_recover(decision: AuthorizationDecision) -> dict[str, Any]:
    return {"type": "ACCESS_RESTORED", "message": "Authorization restored"}


@enforce_till_denied(
    action="stream:heartbeat",
    resource="heartbeat",
    on_stream_deny=_on_deny,
)
async def heartbeat_till_denied(request: HttpRequest):
    """EnforceTillDenied -- stream terminates permanently on first DENY."""
    return _heartbeat_source()


@enforce_drop_while_denied(
    action="stream:heartbeat",
    resource="heartbeat",
)
async def heartbeat_drop_while_denied(request: HttpRequest):
    """EnforceDropWhileDenied -- silently drops events during DENY periods."""
    return _heartbeat_source()


@enforce_recoverable_if_denied(
    action="stream:heartbeat",
    resource="heartbeat",
    on_stream_deny=_on_suspend,
)
async def heartbeat_terminated_by_callback(request: HttpRequest):
    """EnforceRecoverableIfDenied with onStreamDeny only (no recover callback).

    On DENY: sends ACCESS_SUSPENDED event. The stream stays alive and
    resumes forwarding data on re-PERMIT, but no explicit restore signal
    is sent.
    """
    return _heartbeat_source()


@enforce_drop_while_denied(
    action="stream:heartbeat",
    resource="heartbeat",
)
async def heartbeat_drop_with_callbacks(request: HttpRequest):
    """EnforceDropWhileDenied without callbacks.

    Silently drops events during DENY periods. No deny/recover signals
    are sent. The stream stays alive and resumes forwarding on re-PERMIT.
    """
    return _heartbeat_source()


@enforce_recoverable_if_denied(
    action="stream:heartbeat",
    resource="heartbeat",
    on_stream_deny=_on_suspend,
    on_stream_recover=_on_recover,
)
async def heartbeat_recoverable(request: HttpRequest):
    """EnforceRecoverableIfDenied -- sends suspend/restore signals."""
    return _heartbeat_source()
