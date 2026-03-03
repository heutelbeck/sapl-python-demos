# SAPL Django Demo

Demo application for [`sapl-django`](https://github.com/heutelbeck/sapl-python) showing every feature of the library: basic authorization, content filtering, all seven constraint handler interfaces, resource replacement, advice vs obligations, argument manipulation, and streaming SSE with continuous authorization. All endpoints work with plain `curl` except the export endpoint, which requires a JWT from Keycloak. The source files have comprehensive docstrings -- read the code for the full story.

## Quick Start

```bash
docker compose up -d
pip install -e .
uvicorn demo_project.asgi:application --host 0.0.0.0 --port 3000 --reload
```

This starts **Keycloak** on `http://localhost:8080` (admin/admin) with a pre-configured `demo` realm and the **SAPL PDP Node** on `http://localhost:8443` with policies from `./policies/`. Wait about 30 seconds for Keycloak to import the realm.

## Endpoints

### Basic Authorization

```bash
# Health check
curl -s http://localhost:3000/api/ | python3 -m json.tool

# Manual PDP access -- calls pdp_client.decide_once() directly
curl -s http://localhost:3000/api/hello | python3 -m json.tool
```

### Content Filtering

```bash
# SSN blackened (last 4 visible)
curl -s http://localhost:3000/api/patient/P-001 | python3 -m json.tool

# SSN blackened across a list (PostEnforce)
curl -s http://localhost:3000/api/patients | python3 -m json.tool

# Blacken action only (dedicated content-filter endpoint)
curl -s http://localhost:3000/api/content-filter/blacken | python3 -m json.tool

# Blacken + delete + replace combined
curl -s http://localhost:3000/api/content-filter/all-actions | python3 -m json.tool

# Same combined filter via constraint router
curl -s http://localhost:3000/api/constraints/patient | python3 -m json.tool
curl -s http://localhost:3000/api/constraints/patient-full | python3 -m json.tool
```

### Constraint Handlers

```bash
# RunnableConstraintHandlerProvider -- logs to server console
curl -s http://localhost:3000/api/constraints/logged | python3 -m json.tool

# ConsumerConstraintHandlerProvider -- records to audit trail
curl -s http://localhost:3000/api/constraints/audited | python3 -m json.tool
curl -s http://localhost:3000/api/constraints/audit-log | python3 -m json.tool

# MappingConstraintHandlerProvider -- redacts fields
curl -s http://localhost:3000/api/constraints/redacted | python3 -m json.tool

# FilterPredicateConstraintHandlerProvider -- filters array by classification
curl -s http://localhost:3000/api/constraints/documents | python3 -m json.tool

# MethodInvocationConstraintHandlerProvider -- injects timestamp into request
curl -s http://localhost:3000/api/constraints/timestamped | python3 -m json.tool

# ErrorHandlerProvider + ErrorMappingConstraintHandlerProvider -- error pipeline
curl -s http://localhost:3000/api/constraints/error-demo | python3 -m json.tool
```

### Advanced Patterns

```bash
# PDP replaces the endpoint's return value entirely
curl -s http://localhost:3000/api/constraints/resource-replaced | python3 -m json.tool

# Advice (best-effort) -- unhandled advice does NOT deny access
curl -s http://localhost:3000/api/constraints/advised | python3 -m json.tool

# @PostEnforce -- policy sees the actual return data
curl -s http://localhost:3000/api/constraints/record/42 | python3 -m json.tool

# Unhandled obligation -- fail-fast (403 despite PERMIT)
curl -s http://localhost:3000/api/constraints/unhandled | python3 -m json.tool

# Argument manipulation -- amount capped at 5000 by policy
curl -s -X POST 'http://localhost:3000/api/transfer?amount=10000' | python3 -m json.tool
curl -s -X POST 'http://localhost:3000/api/transfer?amount=3000' | python3 -m json.tool
```

### Streaming Authorization (SSE)

The policy cycles PERMIT/DENY based on the current second: 0-19 permit, 20-39 deny, 40-59 permit.

```bash
# Terminates permanently on first DENY
curl -N http://localhost:3000/api/stream/heartbeat

# Silently drops events during DENY, resumes on PERMIT
curl -N http://localhost:3000/api/stream/data

# Sends ACCESS_SUSPENDED / ACCESS_RESTORED signals on transitions
curl -N http://localhost:3000/api/stream/recoverable
```

### Export Data (JWT Required)

The only endpoint requiring authentication. The policy uses `<jwt.token>` to extract claims from the Bearer token and matches the clinician's `pilotId` against the requested `pilotId`. This demonstrates real ABAC where the PDP inspects identity attributes.

**How JWT flows through the system:** The Django view validates the JWT via JWKS. The enforcement code passes the raw token to the PDP via the `secrets` field. The SAPL policy reads `<jwt.token>.payload.pilotId` to make the authorization decision.

**Keycloak** starts automatically with `docker compose up -d` on port 8080 (admin/admin). The `demo` realm has pre-configured test users:

| Username     | Password | Role        | Pilot ID |
|--------------|----------|-------------|----------|
| clinician1   | password | CLINICIAN   | 1        |
| clinician2   | password | CLINICIAN   | 2        |
| participant1 | password | PARTICIPANT | 1        |
| participant2 | password | PARTICIPANT | 2        |

```bash
# Get a token
TOKEN=$(curl -s -X POST 'http://localhost:8080/realms/demo/protocol/openid-connect/token' -H 'Content-Type: application/x-www-form-urlencoded' -d 'grant_type=password' -d 'client_id=demo-app' -d 'client_secret=dev-secret' -d 'username=clinician1' -d 'password=password' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Permitted: clinician1 (pilotId=1) accessing pilot 1 data
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:3000/api/export/1/3 | python3 -m json.tool

# Denied: clinician1 (pilotId=1) accessing pilot 2 data
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:3000/api/export/2/1 | python3 -m json.tool
```

## Reference

### Endpoint Reference

| Path | Enforcement | Auth | Description |
|------|-------------|------|-------------|
| GET /api/ | None | None | Health check |
| GET /api/hello | Manual | None | `pdp_client.decide_once()` |
| GET /api/patient/{id} | `pre_enforce` | None | Blacken SSN |
| GET /api/patients | `post_enforce` | None | List patients, blacken SSN |
| GET /api/export/{p}/{s} | `pre_enforce` | JWT | Custom resource builder, ABAC |
| POST /api/transfer | `pre_enforce` | None | Argument manipulation (cap amount) |
| GET /api/constraints/patient | `pre_enforce` | None | Blacken SSN |
| GET /api/constraints/patient-full | `pre_enforce` | None | Blacken + delete + replace |
| GET /api/constraints/logged | `pre_enforce` | None | RunnableConstraintHandlerProvider |
| GET /api/constraints/audited | `pre_enforce` | None | ConsumerConstraintHandlerProvider |
| GET /api/constraints/audit-log | None | None | View audit trail (auxiliary) |
| GET /api/constraints/redacted | `pre_enforce` | None | MappingConstraintHandlerProvider |
| GET /api/constraints/documents | `pre_enforce` | None | FilterPredicateConstraintHandlerProvider |
| GET /api/constraints/timestamped | `pre_enforce` | None | MethodInvocationConstraintHandlerProvider |
| GET /api/constraints/error-demo | `pre_enforce` | None | ErrorHandler + ErrorMapping |
| GET /api/constraints/resource-replaced | `pre_enforce` | None | PDP resource replacement |
| GET /api/constraints/advised | `pre_enforce` | None | Advice (best-effort) |
| GET /api/constraints/record/{id} | `post_enforce` | None | Return value in subscription |
| GET /api/constraints/unhandled | `pre_enforce` | None | Unhandled obligation (fail-fast) |
| GET /api/content-filter/blacken | `pre_enforce` | None | Blacken action only |
| GET /api/content-filter/all-actions | `pre_enforce` | None | Blacken + delete + replace |
| SSE /api/stream/heartbeat | `enforce_till_denied` | None | Terminal denial |
| SSE /api/stream/data | `enforce_drop_while_denied` | None | Silent drops during DENY |
| SSE /api/stream/recoverable | `enforce_recoverable_if_denied` | None | In-band deny/recover signals |

### Constraint Handler Reference

| Interface | Signature | When It Runs | Demo Handler |
|-----------|-----------|--------------|--------------|
| `RunnableConstraintHandlerProvider` | `() -> None` | On decision, before method | `LogAccessHandler` |
| `ConsumerConstraintHandlerProvider` | `(value) -> None` | After method, side-effect on response | `AuditTrailHandler` |
| `MappingConstraintHandlerProvider` | `(value) -> Any` | After method, transforms response | `RedactFieldsHandler` |
| `FilterPredicateConstraintHandlerProvider` | `(element) -> bool` | After method, filters arrays | `ClassificationFilterHandler` |
| `MethodInvocationConstraintHandlerProvider` | `(ctx: MethodInvocationContext) -> None` | Before method, modifies request/args | `InjectTimestampHandler`, `CapTransferHandler` |
| `ErrorHandlerProvider` | `(error) -> None` | On error, side-effect | `NotifyOnErrorHandler` |
| `ErrorMappingConstraintHandlerProvider` | `(error) -> Exception` | On error, transforms error | `EnrichErrorHandler` |

### Policy Reference

| Policy | Effect | Description |
|--------|--------|-------------|
| permit-read-hello | PERMIT | Any request, action "read", resource "hello" |
| permit-clinician-export | PERMIT | Clinician pilotId match, time-gated (JWT) |
| permit-read-patient | PERMIT + obligation | Blackens SSN via filterJsonContent |
| permit-patient-full | PERMIT + obligation | Blacken + delete + replace combined |
| permit-read-patients | PERMIT + obligation | Blackens SSN across list |
| permit-logged | PERMIT + obligation | logAccess (Runnable) |
| permit-audited | PERMIT + obligation | auditTrail (Consumer) |
| permit-redacted | PERMIT + obligation | redactFields (Mapping) |
| permit-documents | PERMIT + obligation | filterByClassification (FilterPredicate) |
| permit-timestamped | PERMIT + obligation | injectTimestamp (MethodInvocation) |
| permit-error-handling | PERMIT + obligation | notifyOnError + enrichError (error pipeline) |
| permit-replaced | PERMIT + transform | PDP replaces the resource entirely |
| permit-advised | PERMIT + advice | logAccess + unhandled advice (best-effort) |
| permit-read-record | PERMIT | Reads records (PostEnforce) |
| permit-read-audit | PERMIT | Reads audit logs |
| permit-read-secret | PERMIT + obligation | Unknown obligation type (fail-fast) |
| permit-transfer | PERMIT + obligation | capTransferAmount + logAccess |
| streaming-heartbeat-time-based | PERMIT + obligation | Time-based cycling + logAccess |

## Stopping

```bash
docker compose down
```

## License

Apache-2.0
