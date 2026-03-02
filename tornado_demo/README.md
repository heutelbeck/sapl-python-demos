# SAPL Tornado Demo

Demonstrates SAPL policy enforcement in a Tornado application. Shows all enforcement modes (pre/post, service-layer, streaming), constraint handler types, and JWT-based ABAC with Keycloak.

## Quick Start

```bash
docker compose up -d
pip install -e .
python app.py
```

The demo runs on http://localhost:3000 and requires the SAPL PDP and Keycloak containers from `docker-compose.yml`.

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
