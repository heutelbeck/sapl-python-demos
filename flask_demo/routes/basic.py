"""Basic authorization endpoints demonstrating PreEnforce and PostEnforce.

These endpoints show the fundamental ways to enforce policies:
  1. Manual PDP access (pdp_client.decide_once) -- /api/hello
  2. PreEnforce with content filtering (blacken SSN) -- /api/patient/<id>
  3. PostEnforce (authorize after method execution) -- /api/patients
  4. PreEnforce with ABAC (JWT-based export) -- /api/exportData/<p>/<s>
  5. PreEnforce with argument manipulation (cap transfer amount) -- /api/transfer
"""

from __future__ import annotations

import asyncio

import structlog
from flask import Blueprint, abort, g, jsonify, request

from sapl_base.types import AuthorizationDecision, AuthorizationSubscription, Decision
from sapl_flask.decorators import pre_enforce, post_enforce
from sapl_flask.extension import get_sapl_extension

from auth import get_current_user, get_optional_user
from models import PATIENTS

log = structlog.get_logger()

basic_bp = Blueprint("basic", __name__)


@basic_bp.route("/hello")
def get_hello():
    """Manual PDP access -- no decorator.

    Calls pdp_client.decide_once() directly. The policy permit-read-hello
    permits any request with action="read" and resource="hello".
    """
    get_optional_user()

    sapl = get_sapl_extension()
    subscription = AuthorizationSubscription(
        subject="anonymous",
        action="read",
        resource="hello",
    )

    decision = asyncio.run(sapl.pdp_client.decide_once(subscription))
    log.info("PDP decision", decision=decision.decision.value)

    if decision.decision == Decision.PERMIT and not decision.obligations and not decision.has_resource:
        return jsonify({"message": "hello"})

    abort(403, description="Access denied by policy")


@basic_bp.route("/patient/<patient_id>")
@pre_enforce(action="readPatient", resource="patient")
def get_patient(patient_id: str):
    """PreEnforce with content filtering (blacken SSN).

    The policy permit-read-patient permits reading and attaches a
    filterJsonContent obligation that blackens the SSN field.
    """
    for p in PATIENTS:
        if p["id"] == patient_id:
            return dict(p)
    abort(404, description="Patient not found")


@basic_bp.route("/patients")
@post_enforce(action="readPatients", resource="patients")
def get_patients():
    """PostEnforce returning list of patients.

    The endpoint runs first, then the PDP is called with the return value
    available as part of the resource. The policy attaches a content filter
    obligation to blacken SSN fields.
    """
    return [dict(p) for p in PATIENTS]


@basic_bp.route("/exportData/<pilot_id>/<sequence_id>")
@pre_enforce(
    action="exportData",
    resource=lambda ctx: {"pilotId": ctx.params.get("pilot_id", ""), "sequenceId": ctx.params.get("sequence_id", "")},
    secrets=lambda ctx: {"jwt": g.token} if hasattr(g, "token") else None,
)
def get_export_data(pilot_id: str, sequence_id: str):
    """PreEnforce with ABAC (role + pilotId check via JWT).

    The policy permit-clinician-export checks:
    - JWT claim user_role == "CLINICIAN"
    - JWT claim pilotId matches the requested pilotId
    - Time gate based on sequence end dates

    clinician1 (pilotId=1) can access /api/export/1/* but not /api/export/2/*
    """
    get_current_user()
    log.info("exportData", pilot_id=pilot_id, sequence_id=sequence_id)
    return {"pilotId": pilot_id, "sequenceId": sequence_id, "data": "export-payload"}


def _handle_export_deny(decision: AuthorizationDecision):
    """Custom deny handler for exportData2 -- returns structured JSON instead of 403."""
    return {
        "error": "access_denied",
        "decision": decision.decision.value,
    }


@basic_bp.route("/exportData2/<pilot_id>/<sequence_id>")
@pre_enforce(
    action="exportData",
    resource=lambda ctx: {"pilotId": ctx.params.get("pilot_id", ""), "sequenceId": ctx.params.get("sequence_id", "")},
    secrets=lambda ctx: {"jwt": g.token} if hasattr(g, "token") else None,
    on_deny=_handle_export_deny,
)
def get_export_data2(pilot_id: str, sequence_id: str):
    """PreEnforce with onDeny callback.

    Same policy as exportData, but instead of 403 on deny, returns structured
    JSON with the decision details.
    """
    get_current_user()
    log.info("exportData2", pilot_id=pilot_id, sequence_id=sequence_id)
    return {"pilotId": pilot_id, "sequenceId": sequence_id, "data": "export-payload"}


@basic_bp.route("/transfer", methods=["POST"])
def transfer_route():
    """Thin route that parses query params and delegates to the enforced function."""
    amount = request.args.get("amount", 10000.0, type=float)
    recipient = request.args.get("recipient", "default-account")
    return _do_transfer(amount=amount, recipient=recipient)


@pre_enforce(action="transfer", resource="account")
def _do_transfer(amount: float = 10000.0, recipient: str = "default-account"):
    """PreEnforce with argument manipulation (cap amount).

    The CapTransferHandler caps amount via MethodInvocationContext kwargs.
    """
    return {"transferred": amount, "recipient": recipient, "status": "completed"}
