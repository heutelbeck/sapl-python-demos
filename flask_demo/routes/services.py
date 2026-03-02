"""Thin controller for service-layer enforcement demo.

All policy enforcement happens in services/patient_service.py, not here.
This demonstrates that SAPL works at any layer, not just HTTP handlers.
"""

from __future__ import annotations

from flask import Blueprint, abort, jsonify, request

from sapl_base.constraint_bundle import AccessDeniedError

from services import patient_service

services_bp = Blueprint("services", __name__)


@services_bp.route("/patients")
def list_patients():
    """Delegate to PatientService.list_patients()."""
    try:
        return jsonify(patient_service.list_patients())
    except AccessDeniedError:
        abort(403)


@services_bp.route("/patients/find")
def find_patient():
    """Delegate to PatientService.find_patient(name)."""
    name = request.args.get("name", "")
    try:
        return jsonify(patient_service.find_patient(name))
    except AccessDeniedError:
        abort(403)


@services_bp.route("/patients/search")
def search_patients():
    """Delegate to PatientService.search_patients(query)."""
    query = request.args.get("q", "")
    try:
        return jsonify(patient_service.search_patients(query))
    except AccessDeniedError:
        abort(403)


@services_bp.route("/patients/<patient_id>")
def get_patient_detail(patient_id: str):
    """Delegate to PatientService.get_patient_detail(id)."""
    try:
        result = patient_service.get_patient_detail(patient_id)
        if result is None:
            abort(404, description="Patient not found")
        return jsonify(result)
    except AccessDeniedError:
        abort(403)


@services_bp.route("/patients/<patient_id>/summary")
def get_patient_summary(patient_id: str):
    """Delegate to PatientService.get_patient_summary(id)."""
    try:
        result = patient_service.get_patient_summary(patient_id)
        if result is None:
            abort(404, description="Patient not found")
        return jsonify(result)
    except AccessDeniedError:
        abort(403)


@services_bp.route("/transfer", methods=["POST"])
def transfer():
    """Delegate to PatientService.do_transfer(amount)."""
    amount = request.args.get("amount", 10000.0, type=float)
    try:
        return jsonify(patient_service.do_transfer(amount))
    except AccessDeniedError:
        abort(403)
