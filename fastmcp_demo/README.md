# SAPL FastMCP Demo

Demo applications for [`sapl-fastmcp`](https://github.com/heutelbeck/sapl-python) showing two authorization approaches for MCP servers: global SAPL middleware and per-component `auth=sapl()`. Both approaches use Keycloak for JWT authentication and a SAPL PDP for policy-based access control.

## Quick Start

```bash
docker compose up -d
pip install -e .
```

This starts **Keycloak** on `http://localhost:8080` (admin/admin) with a pre-configured `mcp` realm and the **SAPL PDP Node** on `http://localhost:8443` with policies from `./policies/`. Wait about 30 seconds for Keycloak to import the realm.

### Middleware Server (port 8001)

Authorization via `SAPLMiddleware`. A single middleware intercepts all tool calls, resource reads, and prompt gets. Decorator overrides (`@pre_enforce`, `@post_enforce`) customize subscription fields per component.

```bash
python middleware_server.py
```

### Per-Component Auth Server (port 8000)

Authorization via `auth=sapl()` on each tool, resource, and prompt. Each component is individually protected; the PDP controls both visibility (listing) and access.

```bash
python auth_server.py
```

### Client

Exercises all components on either server:

```bash
python client.py saplmiddleware mara
python client.py simpleauthz mara
```

### E2E Demo Script

Fully automated end-to-end test that manages the complete lifecycle:

```bash
python demo.py
```

The script runs through 8 phases:

1. **Cleanup**: Tears down any previous containers and logs.
2. **Infrastructure**: Starts Keycloak and SAPL PDP via `docker compose up`.
3. **Wait**: Polls until Keycloak and PDP are healthy.
4. **Server**: Launches `middleware_server.py` as a subprocess.
5. **Tokens**: Acquires JWT tokens for all four users from Keycloak.
6. **Exercise**: Runs 19 operations per user (listings, tool calls, resource reads, prompt gets) plus an anonymous session.
7. **Report**: Generates `demo-report.md` with per-endpoint decision matrices.
8. **Teardown**: Stops the server and runs `docker compose down`.

**Outputs:**

- `demo-report.md` contains a markdown report showing PERMIT/DENY decisions per user per endpoint.
- `demo-logs/` contains per-user JSON responses and container logs for debugging.

## Users

All passwords match the username. Configured in `keycloak/mcp-realm.json`.

| Username | Role       | Access                                              |
|----------|------------|-----------------------------------------------------|
| mara     | ANALYST    | Customer data, exports, reports (PII with logging)  |
| felix    | ENGINEER   | ML models, pipelines, catalogs                      |
| diana    | COMPLIANCE | Audit logs, purge operations, compliance reviews    |
| sam      | INTERN     | Public data only                                    |

## Authorization Approaches

### Middleware (`middleware_server.py`)

The `SAPLMiddleware` intercepts every MCP operation. The default subscription uses the caller's JWT claims as subject, the operation verb as action, and the component name + arguments as resource. Decorators like `@pre_enforce(action="export_data", stealth=True)` override specific fields or hide components from listings.

### Per-Component Auth (`auth_server.py`)

Each component passes `auth=sapl(...)` with optional overrides for subject, action, resource, environment, and secrets. The PDP evaluates each component independently, so different users see different subsets of tools, resources, and prompts.

## Getting a Token

```bash
TOKEN=$(curl -s -X POST 'http://localhost:8080/realms/mcp/protocol/openid-connect/token' -H 'Content-Type: application/x-www-form-urlencoded' -d 'grant_type=password' -d 'client_id=mcp-server' -d 'username=mara' -d 'password=mara' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

## Stopping

```bash
docker compose down
```

## License

Apache-2.0
