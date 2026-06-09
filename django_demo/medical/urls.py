"""URL configuration for the medical demo app.

Maps all endpoints following the same structure as the NestJS reference demo:
  /api/           -- basic endpoints
  /api/constraints/ -- constraint handler demos (includes content filtering)
  /api/streaming/ -- SSE streaming demos
"""
from __future__ import annotations

from django.urls import path

from medical import views

urlpatterns = [
    # Root
    path("", views.root),

    # Basic endpoints
    path("hello", views.get_hello),
    path("patient/<str:patient_id>", views.get_patient),
    path("patients", views.get_patients),
    path("exportData/<str:pilot_id>/<str:sequence_id>", views.get_export_data),
    path("transfer", views.transfer),

    # Constraint handler demos (includes content filtering)
    path("constraints/patient", views.get_constraint_patient),
    path("constraints/patient-full", views.get_patient_full),
    path("constraints/logged", views.get_logged),
    path("constraints/audited", views.get_audited),
    path("constraints/audit-log", views.get_audit_log),
    path("constraints/redacted", views.get_redacted),
    path("constraints/documents", views.get_documents),
    path("constraints/timestamped", views.get_timestamped),
    path("constraints/error-demo", views.get_error_demo),
    path("constraints/resource-replaced", views.get_resource_replaced),
    path("constraints/advised", views.get_advised),
    path("constraints/record/<str:record_id>", views.get_record),
    path("constraints/unhandled", views.get_unhandled),
    path("constraints/audit", views.get_audit),

    # Streaming
    path("streaming/heartbeat/till-denied", views.heartbeat_till_denied),
    path("streaming/heartbeat/silent-suspending", views.heartbeat_silent_suspending),
    path("streaming/heartbeat/observed-suspending", views.heartbeat_observed_suspending),

    # Service-layer enforcement (enforcement on the PatientService methods)
    path("services/patients", views.service_list_patients),
    path("services/patients/find", views.service_find_patient),
    path("services/patients/search", views.service_search_patients),
    path("services/patients/<str:patient_id>", views.service_patient_detail),
    path("services/patients/<str:patient_id>/summary", views.service_patient_summary),
    path("services/transfer", views.service_transfer),
    path("services/streaming/heartbeat/observed-suspending", views.service_heartbeat_observed_suspending),
]
