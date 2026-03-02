"""Basic authorization endpoints demonstrating PreEnforce and PostEnforce.

These endpoints show the fundamental ways to enforce policies:
  1. Manual PDP access (pdp_client.decide_once) -- /api/hello
  2. PreEnforce with content filtering (blacken SSN) -- /api/patient/<id>
  3. PostEnforce (authorize after method execution) -- /api/patients
  4. PreEnforce with ABAC (JWT-based export) -- /api/exportData/<p>/<s>
  5. PreEnforce with argument manipulation (cap transfer amount) -- /api/transfer
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status

from sapl_base.types import AuthorizationDecision, AuthorizationSubscription, Decision
from sapl_fastapi.decorators import pre_enforce, post_enforce

from app.auth import get_current_user, get_optional_user
from app.models import PATIENTS

log = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["basic"])


@router.get("/hello")
async def get_hello(
    request: Request,
    _user: dict[str, Any] | None = Depends(get_optional_user),
) -> dict[str, Any]:
    """Manual PDP access -- no decorator.

    Calls pdp_client.decide_once() directly. The application code is
    responsible for interpreting the decision and enforcing it manually.

    The policy permit-read-hello permits any request with action="read"
    and resource="hello".
    """
    from sapl_fastapi.dependencies import get_pdp_client

    pdp_client = get_pdp_client()

    subscription = AuthorizationSubscription(
        subject="anonymous",
        action="read",
        resource="hello",
    )
    decision = await pdp_client.decide_once(subscription)
    log.info("PDP decision", decision=decision.decision.value)

    if decision.decision == Decision.PERMIT and not decision.obligations and not decision.has_resource:
        return {"message": "hello"}

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied by policy")


@router.get("/patient/{patient_id}")
@pre_enforce(action="readPatient", resource="patient")
async def get_patient(request: Request, patient_id: str) -> dict[str, Any]:
    """PreEnforce with content filtering (blacken SSN).

    The policy permit-read-patient permits reading and attaches a
    filterJsonContent obligation that blackens the SSN field.
    """
    for p in PATIENTS:
        if p["id"] == patient_id:
            return dict(p)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")


@router.get("/patients")
@post_enforce(action="readPatients", resource="patients")
async def get_patients(request: Request) -> Any:
    """PostEnforce returning list of patients.

    The endpoint runs first, then the PDP is called with the return value
    available as part of the resource. The policy attaches a content filter
    obligation to blacken SSN fields.
    """
    return [dict(p) for p in PATIENTS]


@router.get("/exportData/{pilot_id}/{sequence_id}")
@pre_enforce(
    action="exportData",
    resource=lambda ctx: {"pilotId": ctx.params.get("pilot_id", ""), "sequenceId": ctx.params.get("sequence_id", "")},
    secrets=lambda ctx: {"jwt": getattr(ctx.request.state, "token", None)} if ctx.request and getattr(ctx.request.state, "token", None) else None,
)
async def get_export_data(
    request: Request,
    pilot_id: str,
    sequence_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """PreEnforce with ABAC (role + pilotId check via JWT).

    The policy permit-clinician-export checks:
    - JWT claim user_role == "CLINICIAN"
    - JWT claim pilotId matches the requested pilotId
    - Time gate based on sequence end dates

    clinician1 (pilotId=1) can access /api/export/1/* but not /api/export/2/*
    """
    log.info("exportData", pilot_id=pilot_id, sequence_id=sequence_id)
    return {"pilotId": pilot_id, "sequenceId": sequence_id, "data": "export-payload"}


def _handle_export_deny(decision: AuthorizationDecision) -> dict[str, Any]:
    """Custom deny handler for exportData2 -- returns structured JSON instead of 403."""
    return {
        "error": "access_denied",
        "decision": decision.decision.value,
    }


@router.get("/exportData2/{pilot_id}/{sequence_id}")
@pre_enforce(
    action="exportData",
    resource=lambda ctx: {"pilotId": ctx.params.get("pilot_id", ""), "sequenceId": ctx.params.get("sequence_id", "")},
    secrets=lambda ctx: {"jwt": getattr(ctx.request.state, "token", None)} if ctx.request and getattr(ctx.request.state, "token", None) else None,
    on_deny=_handle_export_deny,
)
async def get_export_data2(
    request: Request,
    pilot_id: str,
    sequence_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """PreEnforce with onDeny callback.

    Same policy as exportData, but instead of 403 on deny, returns structured
    JSON with the decision details.
    """
    log.info("exportData2", pilot_id=pilot_id, sequence_id=sequence_id)
    return {"pilotId": pilot_id, "sequenceId": sequence_id, "data": "export-payload"}


@router.post("/transfer")
@pre_enforce(action="transfer", resource="account")
async def transfer(
    request: Request,
    amount: float = 10000.0,
    recipient: str = "default-account",
) -> dict[str, Any]:
    """PreEnforce with argument manipulation (cap amount).

    The policy permit-transfer attaches a capTransferAmount obligation
    that caps the amount at the policy-specified maximum via the
    MethodInvocationConstraintHandler. The endpoint never sees an amount
    above the cap.
    """
    return {"transferred": amount, "recipient": recipient, "status": "completed"}
