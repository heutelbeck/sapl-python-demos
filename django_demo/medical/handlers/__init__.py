"""SAPL constraint handler providers for the medical demo.

The audit_trail_handler is set by MedicalConfig.ready() so the
audit-log view can access the recorded entries.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from medical.handlers.audit_trail import AuditTrailHandler

audit_trail_handler: AuditTrailHandler | None = None
