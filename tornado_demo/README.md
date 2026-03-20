# SAPL Tornado Demo

Demonstrates SAPL policy enforcement in a Tornado application. Shows all enforcement modes (pre/post, service-layer, streaming), constraint handler types, and JWT-based ABAC with Keycloak.

## Prerequisites

- Python 3.12+
- Docker (for Keycloak and SAPL Node)

## Quick Start

```bash
docker compose up -d
python -m venv .venv
source .venv/bin/activate
pip install -e .
python app.py
```

This starts **Keycloak** on `http://localhost:8080` and the **SAPL PDP Node** on `http://localhost:8443`. Keycloak takes about 30 seconds to import the realm on first start. Wait until `curl -s http://localhost:8080/realms/demo` returns JSON before running the app. The demo runs on http://localhost:3000.

## Endpoint Reference

| Endpoint | Method | Enforcement | Policy |
|----------|--------|-------------|--------|
| `/api/hello` | GET | Manual PDP | permit-read-hello |
| `/api/patient/:id` | GET | PreEnforce | permit-read-patient (blacken SSN) |
| `/api/patients` | GET | PostEnforce | permit-read-patients (blacken SSN) |
| `/api/transfer` | POST | PreEnforce | permit-transfer (cap amount) |
| `/api/exportData/:p/:s` | GET | PreEnforce+JWT | permit-clinician-export |
| `/api/constraints/logged` | GET | PreEnforce | permit-logged (logAccess) |
| `/api/constraints/audited` | GET | PreEnforce | permit-audited (auditTrail) |
| `/api/constraints/redacted` | GET | PreEnforce | permit-redacted (redactFields) |
| `/api/constraints/patient` | GET | PreEnforce | permit-read-patient (filterJsonContent) |
| `/api/constraints/patient-full` | GET | PreEnforce | permit-patient-full (blacken+delete+replace) |
| `/api/constraints/documents` | GET | PreEnforce | permit-documents (filterByClassification) |
| `/api/constraints/timestamped` | GET | PreEnforce | permit-timestamped (injectTimestamp) |
| `/api/constraints/error-demo` | GET | PreEnforce | permit-error-handling (error pipeline) |
| `/api/constraints/resource-replaced` | GET | PreEnforce | permit-replaced (transform) |
| `/api/constraints/advised` | GET | PreEnforce | permit-advised (best-effort advice) |
| `/api/constraints/unhandled` | GET | PreEnforce | permit-read-secret (unhandled obligation -> 403) |
| `/api/streaming/heartbeat/*` | GET | Streaming | streaming-heartbeat-time-based |
| `/api/services/*` | GET/POST | Service-layer | permit-service-* |

## Test Users (Keycloak)

| User | Password | Role | pilotId |
|------|----------|------|---------|
| clinician1 | password | CLINICIAN | 1 |
| clinician2 | password | CLINICIAN | 2 |
| participant1 | password | PARTICIPANT | 1 |
| participant2 | password | PARTICIPANT | 2 |

## License

Apache-2.0
