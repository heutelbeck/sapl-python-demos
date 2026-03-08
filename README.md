# SAPL Python Demo Applications

Demo applications showing SAPL policy enforcement integrated with Python web frameworks. Each demo connects to a SAPL PDP and a Keycloak identity provider running in Docker.

## Demos

| Demo | Framework | Description |
|------|-----------|-------------|
| [fastapi_demo](fastapi_demo/) | FastAPI | Full-featured demo with JWT, SSE streaming, content filtering, and all constraint handler types |
| [django_demo](django_demo/) | Django 5 | Medical records domain with JWT, async views, and streaming |
| [flask_demo](flask_demo/) | Flask | Minimal integration example with pre/post enforce and constraint handlers |
| [fastmcp_demo](fastmcp_demo/) | FastMCP (MCP) | SAPL middleware and per-component auth for MCP tools, resources, and prompts |

## Prerequisites

- Docker and Docker Compose
- Python 3.12+
- pip

## Quick Start

Each demo is self-contained. To run any demo:

### 1. Start infrastructure

```
cd fastapi_demo
docker compose up -d
```

This starts a SAPL PDP Node on `https://localhost:8443` and a Keycloak instance on `http://localhost:8080`. Wait roughly 30 seconds for Keycloak to finish importing the realm.

### 2. Install dependencies

```
pip install -e .
```

### 3. Run the application

FastAPI demo:
```
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

Django demo:
```
uvicorn demo_project.asgi:application --host 0.0.0.0 --port 3000 --reload
```

Flask demo:
```
python app.py
```

All demos expose their API on `http://localhost:3000`.

## Architecture

Each demo includes:

- A SAPL PDP Node configured with policies from the local `policies/` directory
- Keycloak configured with a pre-built realm (users, roles, client credentials)
- Application code demonstrating enforcement decorators from the corresponding `sapl-*` library
- Constraint handler implementations (runnable, consumer, mapping, filter predicate, method invocation)

The FastAPI and Django demos include JWT-based ABAC, SSE streaming endpoints, and the full range of constraint handler types. The Flask demo covers pre/post enforcement and basic constraint handlers.

## Getting a Token

All demos use Keycloak. To obtain a JWT for testing authenticated endpoints:

FastAPI demo:
```
TOKEN=$(curl -s -X POST http://localhost:8080/realms/demo/protocol/openid-connect/token -H "Content-Type: application/x-www-form-urlencoded" -d "grant_type=password&client_id=demo-app&client_secret=dev-secret&username=clinician1&password=password" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

Django demo:
```
TOKEN=$(curl -s -X POST http://localhost:8080/realms/demo/protocol/openid-connect/token -H "Content-Type: application/x-www-form-urlencoded" -d "grant_type=password&client_id=demo-app&client_secret=dev-secret&username=clinician1&password=password" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

Flask demo:
```
TOKEN=$(curl -s -X POST http://localhost:8080/realms/demo/protocol/openid-connect/token -H "Content-Type: application/x-www-form-urlencoded" -d "grant_type=password&client_id=demo-app&client_secret=dev-secret&username=clinician1&password=password" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

Available test users (password: `password`):

| Username | Role | pilotId |
|----------|------|---------|
| clinician1 | CLINICIAN | 1 |
| clinician2 | CLINICIAN | 2 |
| participant1 | PARTICIPANT | 1 |
| participant2 | PARTICIPANT | 2 |

## Related

- Library repository: [heutelbeck/sapl-python](https://github.com/heutelbeck/sapl-python)
- Documentation: [sapl.io/docs](https://sapl.io/docs/latest/8_1_PEPImplementationSpecification/)
- SAPL project: [sapl.io](https://sapl.io)
