"""Basic authorization endpoints demonstrating PreEnforce and PostEnforce.

These endpoints show the fundamental ways to enforce policies:
  1. Manual PDP access (pdp_client.decide_once) -- /api/hello
  2. PreEnforce with content filtering (blacken SSN) -- /api/patient/<id>
  3. PostEnforce (authorize after method execution) -- /api/patients
  4. PreEnforce with ABAC (JWT-based export) -- /api/exportData/<p>/<s>
  5. PreEnforce with argument manipulation (cap transfer amount) -- /api/transfer
"""

from __future__ import annotations

import json

import structlog
import tornado.web

from sapl_base.types import AuthorizationDecision, AuthorizationSubscription, Decision
from sapl_tornado.decorators import post_enforce, pre_enforce
from sapl_tornado.dependencies import get_pdp_client

from auth import get_current_user, get_optional_user
from models import PATIENTS

log = structlog.get_logger()


def _extract_bearer_secret(ctx) -> dict[str, str] | None:
    """Extract Bearer token from request headers for the PDP secrets field."""
    if ctx.request is None:
        return None
    auth_header = ctx.request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return {"jwt": auth_header[len("Bearer "):]}
    return None


class HelloHandler(tornado.web.RequestHandler):
    """Manual PDP access -- no decorator."""

    async def get(self):
        get_optional_user(self)

        subscription = AuthorizationSubscription(
            subject="anonymous",
            action="read",
            resource="hello",
        )

        decision = await get_pdp_client().decide_once(subscription)
        log.info("PDP decision", decision=decision.decision.value)

        if decision.decision == Decision.PERMIT and not decision.obligations and not decision.has_resource:
            self.set_header("Content-Type", "application/json; charset=UTF-8")
            self.write(json.dumps({"message": "hello"}))
            return

        raise tornado.web.HTTPError(403, reason="Access denied by policy")


class PatientHandler(tornado.web.RequestHandler):
    """PreEnforce with content filtering (blacken SSN)."""

    @pre_enforce(action="readPatient", resource="patient")
    async def get(self, patient_id):
        for p in PATIENTS:
            if p["id"] == patient_id:
                return dict(p)
        raise tornado.web.HTTPError(404, reason="Patient not found")


class PatientsHandler(tornado.web.RequestHandler):
    """PostEnforce returning list of patients."""

    @post_enforce(action="readPatients", resource="patients")
    async def get(self):
        return [dict(p) for p in PATIENTS]


class ExportDataHandler(tornado.web.RequestHandler):
    """PreEnforce with ABAC (role + pilotId check via JWT)."""

    @pre_enforce(
        action="exportData",
        resource=lambda ctx: {"pilotId": ctx.params.get("pilot_id", ""), "sequenceId": ctx.params.get("sequence_id", "")},
        secrets=lambda ctx: _extract_bearer_secret(ctx),
    )
    async def get(self, pilot_id, sequence_id):
        get_current_user(self)
        log.info("exportData", pilot_id=pilot_id, sequence_id=sequence_id)
        return {"pilotId": pilot_id, "sequenceId": sequence_id, "data": "export-payload"}


def _handle_export_deny(decision: AuthorizationDecision):
    """Custom deny handler for exportData2 -- returns structured JSON instead of 403."""
    return {"error": "access_denied", "decision": decision.decision.value}


class ExportData2Handler(tornado.web.RequestHandler):
    """PreEnforce with onDeny callback."""

    @pre_enforce(
        action="exportData",
        resource=lambda ctx: {"pilotId": ctx.params.get("pilot_id", ""), "sequenceId": ctx.params.get("sequence_id", "")},
        secrets=lambda ctx: _extract_bearer_secret(ctx),
        on_deny=_handle_export_deny,
    )
    async def get(self, pilot_id, sequence_id):
        get_current_user(self)
        log.info("exportData2", pilot_id=pilot_id, sequence_id=sequence_id)
        return {"pilotId": pilot_id, "sequenceId": sequence_id, "data": "export-payload"}


class TransferHandler(tornado.web.RequestHandler):
    """Thin route that parses query params and delegates to the enforced function."""

    async def post(self):
        amount = float(self.get_argument("amount", "10000.0"))
        recipient = self.get_argument("recipient", "default-account")
        result = await _do_transfer(amount=amount, recipient=recipient)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(result))


@pre_enforce(action="transfer", resource="account")
async def _do_transfer(amount: float = 10000.0, recipient: str = "default-account"):
    """PreEnforce with argument manipulation (cap amount)."""
    return {"transferred": amount, "recipient": recipient, "status": "completed"}


BasicHandlers = [
    (r"/api/hello", HelloHandler),
    (r"/api/patient/(?P<patient_id>[^/]+)", PatientHandler),
    (r"/api/patients", PatientsHandler),
    (r"/api/exportData/(?P<pilot_id>[^/]+)/(?P<sequence_id>[^/]+)", ExportDataHandler),
    (r"/api/exportData2/(?P<pilot_id>[^/]+)/(?P<sequence_id>[^/]+)", ExportData2Handler),
    (r"/api/transfer", TransferHandler),
]
