"""Thin controller for service-layer enforcement demo.

All policy enforcement happens in services/patient_service.py, not here.
This demonstrates that SAPL works at any layer, not just HTTP handlers.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.services import patient_service

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("/patients")
async def list_patients() -> Any:
    """Delegate to PatientService.list_patients()."""
    return await patient_service.list_patients()


@router.get("/patients/find")
async def find_patient(name: str = "") -> Any:
    """Delegate to PatientService.find_patient(name)."""
    return await patient_service.find_patient(name)


@router.get("/patients/search")
async def search_patients(q: str = "") -> Any:
    """Delegate to PatientService.search_patients(query)."""
    return await patient_service.search_patients(q)


@router.get("/patients/{patient_id}")
async def get_patient_detail(patient_id: str) -> Any:
    """Delegate to PatientService.get_patient_detail(id)."""
    result = await patient_service.get_patient_detail(patient_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return result


@router.get("/patients/{patient_id}/summary")
async def get_patient_summary(patient_id: str) -> Any:
    """Delegate to PatientService.get_patient_summary(id)."""
    result = await patient_service.get_patient_summary(patient_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return result


@router.post("/transfer")
async def transfer(amount: float = 10000.0) -> Any:
    """Delegate to PatientService.do_transfer(amount)."""
    return await patient_service.do_transfer(amount)
