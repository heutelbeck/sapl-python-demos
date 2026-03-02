"""In-memory domain models and sample data for the medical demo.

No Django ORM models are needed -- this demo uses plain dictionaries
to keep the focus on SAPL policy enforcement rather than persistence.
"""
from __future__ import annotations

PATIENTS: list[dict] = [
    {
        "id": "P-001",
        "name": "Jane Doe",
        "ssn": "123-45-6789",
        "diagnosis": "healthy",
        "classification": "INTERNAL",
        "email": "jane.doe@example.com",
        "internal_notes": "Follow-up scheduled for next week",
    },
    {
        "id": "P-002",
        "name": "John Smith",
        "ssn": "987-65-4321",
        "diagnosis": "checkup",
        "classification": "CONFIDENTIAL",
        "email": "john.smith@example.com",
        "internal_notes": None,
    },
    {
        "id": "P-003",
        "name": "Alice Johnson",
        "ssn": "555-12-3456",
        "diagnosis": "healthy",
        "classification": "PUBLIC",
        "email": "alice.j@example.com",
        "internal_notes": None,
    },
]

DOCUMENTS: list[dict] = [
    {"id": "DOC-1", "title": "Company Newsletter", "classification": "PUBLIC"},
    {"id": "DOC-2", "title": "Team Standup Notes", "classification": "INTERNAL"},
    {"id": "DOC-3", "title": "Patient Records", "classification": "CONFIDENTIAL"},
    {"id": "DOC-4", "title": "Encryption Keys", "classification": "SECRET"},
]
