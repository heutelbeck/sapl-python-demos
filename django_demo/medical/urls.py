"""URL configuration for the medical demo app.

Maps all endpoints following the same structure as the NestJS reference demo:
  /api/           -- basic endpoints
  /api/constraints/ -- constraint handler demos (includes content filtering)
  /api/streaming/ -- SSE streaming demos
"""
from __future__ import annotations

from django.urls import path

from medical import views, views_services

urlpatterns = [
    # Root
    path("", views.root),

    # Basic endpoints
    path("hello", views.get_hello),
    path("patient/<str:patient_id>", views.get_patient),
    path("patients", views.get_patients),
    path("exportData/<str:pilot_id>/<str:sequence_id>", views.get_export_data),
    path("exportData2/<str:pilot_id>/<str:sequence_id>", views.get_export_data2),
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
    path("streaming/heartbeat/drop-while-denied", views.heartbeat_drop_while_denied),
    path("streaming/heartbeat/terminated-by-callback", views.heartbeat_terminated_by_callback),
    path("streaming/heartbeat/drop-with-callbacks", views.heartbeat_drop_with_callbacks),
    path("streaming/heartbeat/recoverable", views.heartbeat_recoverable),

    # Service-layer enforcement
    path("services/patients", views_services.list_patients),
    path("services/patients/find", views_services.find_patient),
    path("services/patients/search", views_services.search_patients),
    path("services/patients/<str:patient_id>", views_services.get_patient_detail),
    path("services/patients/<str:patient_id>/summary", views_services.get_patient_summary),
    path("services/transfer", views_services.transfer),
]
