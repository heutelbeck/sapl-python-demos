"""Thin controller for service-layer enforcement demo.

All policy enforcement happens in services/patient_service.py, not here.
This demonstrates that SAPL works at any layer, not just HTTP handlers.
"""

from __future__ import annotations

from django.http import HttpRequest, JsonResponse

from sapl_base.constraint_bundle import AccessDeniedError

from medical.services import patient_service


def _json_error(status: int, detail: str) -> JsonResponse:
    return JsonResponse({"detail": detail}, status=status)


async def list_patients(request: HttpRequest) -> JsonResponse:
    """Delegate to PatientService.list_patients()."""
    try:
        result = await patient_service.list_patients()
        return JsonResponse(result, safe=False)
    except AccessDeniedError:
        return _json_error(403, "Access denied")


async def find_patient(request: HttpRequest) -> JsonResponse:
    """Delegate to PatientService.find_patient(name)."""
    name = request.GET.get("name", "")
    try:
        result = await patient_service.find_patient(name)
        return JsonResponse(result, safe=False)
    except AccessDeniedError:
        return _json_error(403, "Access denied")


async def search_patients(request: HttpRequest) -> JsonResponse:
    """Delegate to PatientService.search_patients(query)."""
    query = request.GET.get("q", "")
    try:
        result = await patient_service.search_patients(query)
        return JsonResponse(result, safe=False)
    except AccessDeniedError:
        return _json_error(403, "Access denied")


async def get_patient_detail(request: HttpRequest, patient_id: str) -> JsonResponse:
    """Delegate to PatientService.get_patient_detail(id)."""
    try:
        result = await patient_service.get_patient_detail(patient_id)
        if result is None:
            return _json_error(404, "Patient not found")
        return JsonResponse(result)
    except AccessDeniedError:
        return _json_error(403, "Access denied")


async def get_patient_summary(request: HttpRequest, patient_id: str) -> JsonResponse:
    """Delegate to PatientService.get_patient_summary(id)."""
    try:
        result = await patient_service.get_patient_summary(patient_id)
        if result is None:
            return _json_error(404, "Patient not found")
        return JsonResponse(result)
    except AccessDeniedError:
        return _json_error(403, "Access denied")


async def transfer(request: HttpRequest) -> JsonResponse:
    """Delegate to PatientService.do_transfer(amount)."""
    if request.method != "POST":
        return _json_error(405, "Method not allowed")
    amount = float(request.GET.get("amount", "10000"))
    try:
        result = await patient_service.do_transfer(amount)
        return JsonResponse(result)
    except AccessDeniedError:
        return _json_error(403, "Access denied")
