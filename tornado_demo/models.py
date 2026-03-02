"""Data models and in-memory sample data for the Flask demo."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Patient:
    """Patient record used across the demo endpoints."""

    id: str
    name: str
    ssn: str
    diagnosis: str
    classification: str
    email: str | None = None
    internal_notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "ssn": self.ssn,
            "diagnosis": self.diagnosis,
            "classification": self.classification,
        }
        if self.email is not None:
            result["email"] = self.email
        if self.internal_notes is not None:
            result["internal_notes"] = self.internal_notes
        return result


@dataclass
class TransferRequest:
    """Request body for the fund transfer endpoint."""

    amount: float = 10000.0
    recipient: str = "default-account"


DOCUMENTS: list[dict[str, Any]] = [
    {"id": "DOC-1", "title": "Company Newsletter", "classification": "PUBLIC"},
    {"id": "DOC-2", "title": "Team Standup Notes", "classification": "INTERNAL"},
    {"id": "DOC-3", "title": "Patient Records", "classification": "CONFIDENTIAL"},
    {"id": "DOC-4", "title": "Encryption Keys", "classification": "SECRET"},
]

PATIENTS: list[dict[str, Any]] = [
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
