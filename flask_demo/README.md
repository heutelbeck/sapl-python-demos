# SAPL Flask Demo

Demo application for [`sapl-flask`](https://github.com/heutelbeck/sapl-python) showing every feature of the library: basic authorization, content filtering, the full constraint handler signal taxonomy (DECISION / INPUT / OUTPUT / ERROR), resource replacement, advice vs obligations, argument manipulation, and streaming SSE with continuous authorization. All endpoints work with plain `curl` except the export endpoint, which requires a JWT from Keycloak. The source files have comprehensive docstrings -- read the code for the full story.

URL structure follows the [NestJS reference demo](https://github.com/heutelbeck/sapl-nestjs-demo). Content filtering is demonstrated under `/api/constraints/` (not as a separate router) since the NestJS demo combines them there.

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

This starts **Keycloak** on `http://localhost:8080` (admin/admin) with a pre-configured `demo` realm and the **SAPL PDP Node** on `http://localhost:8443` with policies from `./policies/`. Keycloak takes about 30 seconds to import the realm on first start. Wait until `curl -s http://localhost:8080/realms/demo` returns JSON before running the app.

## Endpoints

### Basic Authorization

```bash
# Manual PDP access -- calls pdp_client.decide_once() directly
curl -s http://localhost:3000/api/hello | python3 -m json.tool

# SSN blackened (last 4 visible)
curl -s http://localhost:3000/api/patient/P-001 | python3 -m json.tool

# SSN blackened across a list (PostEnforce)
curl -s http://localhost:3000/api/patients | python3 -m json.tool
```

### Constraint Handlers

```bash
# Content filter: blacken SSN
curl -s http://localhost:3000/api/constraints/patient | python3 -m json.tool

# Content filter: blacken + delete + replace combined
curl -s http://localhost:3000/api/constraints/patient-full | python3 -m json.tool

# DECISION runner -- logs to server console
curl -s http://localhost:3000/api/constraints/logged | python3 -m json.tool

# OUTPUT consumer -- records to audit trail
curl -s http://localhost:3000/api/constraints/audited | python3 -m json.tool
curl -s http://localhost:3000/api/constraints/audit-log | python3 -m json.tool

# OUTPUT mapper -- redacts fields
curl -s http://localhost:3000/api/constraints/redacted | python3 -m json.tool

# OUTPUT mapper with DROP sentinel -- filters list by classification
curl -s http://localhost:3000/api/constraints/documents | python3 -m json.tool

# INPUT mapper -- injects timestamp into kwargs
curl -s http://localhost:3000/api/constraints/timestamped | python3 -m json.tool

# ERROR consumer + ERROR mapper -- error pipeline
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

The policy cycles on the current second: 0-19 permit, 20-39 closed, 40-59 permit. In the
closed window the `stream:terminate` action is denied and `stream:suspend` is suspended.

```bash
# Terminates permanently on first DENY
curl -N http://localhost:3000/api/streaming/heartbeat/till-denied

# Silently drops events while suspended, resumes on PERMIT
curl -N http://localhost:3000/api/streaming/heartbeat/silent-suspending

# Sends ACCESS_SUSPENDED / ACCESS_GRANTED frames on transitions
curl -N http://localhost:3000/api/streaming/heartbeat/observed-suspending
```

### Export Data (JWT Required)

The only endpoint requiring authentication. The policy uses `<jwt.token>` to extract claims from the Bearer token and matches the clinician's `pilotId` against the requested `pilotId`. This demonstrates real ABAC where the PDP inspects identity attributes.

**How JWT flows through the system:** Flask validates the JWT via JWKS. The enforcement code passes the raw token to the PDP via the `secrets` field. The SAPL policy reads `<jwt.token>.payload.pilotId` to make the authorization decision.

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
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:3000/api/exportData/1/1 | python3 -m json.tool

# Denied: clinician1 (pilotId=1) accessing pilot 2 data
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:3000/api/exportData/2/1 | python3 -m json.tool
```

## Reference

### Endpoint Reference

| Path | Enforcement | Auth | Description |
|------|-------------|------|-------------|
| GET /api/hello | Manual | None | `pdp_client.decide_once()` |
| GET /api/patient/{id} | `pre_enforce` | None | Blacken SSN |
| GET /api/patients | `post_enforce` | None | List patients, blacken SSN |
| GET /api/exportData/{p}/{s} | `pre_enforce` | JWT | Custom resource builder, ABAC |
| POST /api/transfer | `pre_enforce` | None | Argument manipulation (cap amount) |
| GET /api/constraints/patient | `pre_enforce` | None | Blacken SSN |
| GET /api/constraints/patient-full | `pre_enforce` | None | Blacken + delete + replace |
| GET /api/constraints/logged | `pre_enforce` | None | DECISION runner |
| GET /api/constraints/audited | `pre_enforce` | None | OUTPUT consumer |
| GET /api/constraints/audit-log | None | None | View audit trail (auxiliary) |
| GET /api/constraints/redacted | `pre_enforce` | None | OUTPUT mapper |
| GET /api/constraints/documents | `pre_enforce` | None | OUTPUT mapper using DROP sentinel |
| GET /api/constraints/timestamped | `pre_enforce` | None | INPUT mapper |
| GET /api/constraints/error-demo | `pre_enforce` | None | ERROR consumer + ERROR mapper |
| GET /api/constraints/resource-replaced | `pre_enforce` | None | PDP resource replacement |
| GET /api/constraints/advised | `pre_enforce` | None | Advice (best-effort) |
| GET /api/constraints/record/{id} | `post_enforce` | None | Return value in subscription |
| GET /api/constraints/unhandled | `pre_enforce` | None | Unhandled obligation (fail-fast) |
| SSE /api/streaming/heartbeat/till-denied | `stream_enforce` | None | Terminal denial on DENY |
| SSE /api/streaming/heartbeat/silent-suspending | `stream_enforce` (`pause_rap_during_suspend=True`) | None | Silent drops during SUSPEND |
| SSE /api/streaming/heartbeat/observed-suspending | `stream_enforce` (`signal_transitions=True`, `pause_rap_during_suspend=True`) | None | In-band SUSPEND/RESTORED signals |

### Constraint Handler Reference

Every provider implements `ConstraintHandlerProvider.get_handlers(constraint) -> Sequence[ScopedHandler]`.
A `ScopedHandler` is a triple of `(signal, shape, priority)`:

- **Signal**: `DECISION`, `INPUT`, `OUTPUT`, or `ERROR`. Where the handler fires.
- **Shape**: `runner` (no value), `consumer` (observes value), or `mapper` (transforms value).
- **Priority**: integer; lower fires first. Same-priority mappers must commute.

| Demo Handler | Signal | Shape | Notes |
|--------------|--------|-------|-------|
| `LogAccessHandler` | `DECISION` | runner | Side-effect on every decision |
| `AuditTrailHandler` | `OUTPUT` | consumer | Records response to in-memory log |
| `RedactFieldsHandler` | `OUTPUT` | mapper | Blackens / replaces / deletes fields |
| `ClassificationFilterHandler` | `OUTPUT` | mapper | Walks list, drops elements by classification |
| `InjectTimestampHandler` | `INPUT` | mapper | Adds `policy_timestamp` to kwargs |
| `CapTransferHandler` | `INPUT` | mapper | Clamps `amount` kwarg |
| `NotifyOnErrorHandler` | `ERROR` | consumer | Side-effect on exception |
| `EnrichErrorHandler` | `ERROR` | mapper | Wraps exception with support URL |

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
