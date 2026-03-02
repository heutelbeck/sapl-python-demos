"""Service-layer enforcement demo.

Mirrors the NestJS PatientService pattern: policy enforcement happens on
service methods rather than HTTP handlers. The thin controller in
routers/services.py delegates to these methods.

Uses ``@service_pre_enforce`` / ``@service_post_enforce`` decorators from
sapl_fastapi, which handle subscription building and PDP communication
without catching ``AccessDeniedError`` (the caller handles HTTP responses).
"""

from __future__ import annotations

from typing import Any

from sapl_fastapi.decorators import service_post_enforce, service_pre_enforce

from app.models import PATIENTS


@service_pre_enforce(action="service:listPatients", resource="patients")
async def list_patients() -> list[dict[str, Any]]:
    """List all patients. Policy: permit-service-list-patients."""
    return [dict(p) for p in PATIENTS]


@service_pre_enforce(action="service:findPatient", resource="patient")
async def find_patient(name: str) -> list[dict[str, Any]]:
    """Find patients by name substring. Policy: permit-service-find-patient."""
    return [dict(p) for p in PATIENTS if name.lower() in p["name"].lower()]


@service_post_enforce(
    action="service:getPatientDetail",
    resource=lambda ctx: {"type": "patientDetail", "data": ctx.return_value},
)
async def get_patient_detail(patient_id: str) -> dict[str, Any] | None:
    """Get full patient detail. Policy: permit-service-patient-detail (PostEnforce)."""
    for p in PATIENTS:
        if p["id"] == patient_id:
            return dict(p)
    return None


@service_pre_enforce(action="service:getPatientSummary", resource="patientSummary")
async def get_patient_summary(patient_id: str) -> dict[str, Any] | None:
    """Get patient summary with insurance. Policy: permit-service-patient-summary."""
    for p in PATIENTS:
        if p["id"] == patient_id:
            result = dict(p)
            result["insurance"] = "INS-9876-XYZ"
            return result
    return None


@service_pre_enforce(action="service:searchPatients", resource="patientSearch")
async def search_patients(query: str) -> list[dict[str, Any]]:
    """Search patients by name or diagnosis. Policy: permit-service-search-patients."""
    q = query.lower()
    return [
        dict(p) for p in PATIENTS
        if q in p["name"].lower() or q in p["diagnosis"].lower()
    ]


@service_pre_enforce(action="service:transfer", resource="account")
async def do_transfer(amount: float = 10000.0) -> dict[str, Any]:
    """Execute a fund transfer. Policy: permit-service-transfer."""
    return {"transferred": amount, "status": "completed"}
