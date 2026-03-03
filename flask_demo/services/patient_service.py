"""Service-layer enforcement demo.

Mirrors the NestJS PatientService pattern: policy enforcement happens on
service methods rather than HTTP handlers. The thin controller in
routes/services.py delegates to these methods.

Uses ``@pre_enforce`` / ``@post_enforce`` decorators from sapl_flask.
``AccessDeniedError`` propagates to the caller (or global error handler).
"""

from __future__ import annotations

from typing import Any

from sapl_flask.decorators import post_enforce, pre_enforce

from models import PATIENTS


@pre_enforce(action="listPatients", resource="patients")
def list_patients() -> list[dict[str, Any]]:
    """List all patients. Policy: permit-service-list-patients."""
    return [dict(p) for p in PATIENTS]


@pre_enforce(action="findPatient", resource="patient")
def find_patient(name: str) -> list[dict[str, Any]]:
    """Find patients by name substring. Policy: permit-service-find-patient."""
    return [dict(p) for p in PATIENTS if name.lower() in p["name"].lower()]


@post_enforce(
    action="getPatientDetail",
    resource=lambda ctx: {"type": "patientDetail", "data": ctx.return_value},
)
def get_patient_detail(patient_id: str) -> dict[str, Any] | None:
    """Get full patient detail. Policy: permit-service-patient-detail (PostEnforce)."""
    for p in PATIENTS:
        if p["id"] == patient_id:
            return dict(p)
    return None


@pre_enforce(action="getPatientSummary", resource="patientSummary")
def get_patient_summary(patient_id: str) -> dict[str, Any] | None:
    """Get patient summary with insurance. Policy: permit-service-patient-summary."""
    for p in PATIENTS:
        if p["id"] == patient_id:
            result = dict(p)
            result["insurance"] = "INS-9876-XYZ"
            return result
    return None


@pre_enforce(action="searchPatients", resource="patientSearch")
def search_patients(query: str) -> list[dict[str, Any]]:
    """Search patients by name or diagnosis. Policy: permit-service-search-patients."""
    q = query.lower()
    return [
        dict(p) for p in PATIENTS
        if q in p["name"].lower() or q in p["diagnosis"].lower()
    ]


@pre_enforce(action="transfer", resource="account")
def do_transfer(amount: float = 10000.0) -> dict[str, Any]:
    """Execute a fund transfer. Policy: permit-service-transfer."""
    return {"transferred": amount, "status": "completed"}
