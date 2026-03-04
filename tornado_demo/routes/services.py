"""Thin controller for service-layer enforcement demo.

All policy enforcement happens in services/patient_service.py, not here.
This demonstrates that SAPL works at any layer, not just HTTP handlers.
"""

from __future__ import annotations

import json

import tornado.web

from services import patient_service


class ServicePatientsHandler(tornado.web.RequestHandler):
    """Delegate to PatientService.list_patients()."""

    async def get(self):
        result = await patient_service.list_patients()
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(result))


class ServiceFindPatientHandler(tornado.web.RequestHandler):
    """Delegate to PatientService.find_patient(name)."""

    async def get(self):
        name = self.get_argument("name", "")
        result = await patient_service.find_patient(name)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(result))


class ServiceSearchPatientsHandler(tornado.web.RequestHandler):
    """Delegate to PatientService.search_patients(query)."""

    async def get(self):
        query = self.get_argument("q", "")
        result = await patient_service.search_patients(query)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(result))


class ServicePatientDetailHandler(tornado.web.RequestHandler):
    """Delegate to PatientService.get_patient_detail(id)."""

    async def get(self, patient_id):
        result = await patient_service.get_patient_detail(patient_id)
        if result is None:
            raise tornado.web.HTTPError(404, reason="Patient not found")
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(result))


class ServicePatientSummaryHandler(tornado.web.RequestHandler):
    """Delegate to PatientService.get_patient_summary(id)."""

    async def get(self, patient_id):
        result = await patient_service.get_patient_summary(patient_id)
        if result is None:
            raise tornado.web.HTTPError(404, reason="Patient not found")
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(result))


class ServiceTransferHandler(tornado.web.RequestHandler):
    """Delegate to PatientService.do_transfer(amount)."""

    async def post(self):
        amount = float(self.get_argument("amount", "10000.0"))
        result = await patient_service.do_transfer(amount)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(result))


ServiceHandlers = [
    (r"/api/services/patients/find", ServiceFindPatientHandler),
    (r"/api/services/patients/search", ServiceSearchPatientsHandler),
    (r"/api/services/patients/(?P<patient_id>[^/]+)/summary", ServicePatientSummaryHandler),
    (r"/api/services/patients/(?P<patient_id>[^/]+)", ServicePatientDetailHandler),
    (r"/api/services/patients", ServicePatientsHandler),
    (r"/api/services/transfer", ServiceTransferHandler),
]
