#!/usr/bin/env python3
"""End-to-end exercise of the SAPL MCP analytics demo.

Spins up Keycloak + SAPL PDP + MCP server, exercises every endpoint
as every user (including anonymous), captures all output, and produces
an MD summary report organized per endpoint.

Run with:  .venv/bin/python demo.py
"""

import atexit
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
MCP_DIR = SCRIPT_DIR
LOG_DIR = SCRIPT_DIR / "demo-logs"
REPORT = SCRIPT_DIR / "demo-report.md"
VENV_PYTHON = SCRIPT_DIR / ".venv" / "bin" / "python"

MCP_ENDPOINT = "http://localhost:8001/mcp"
KEYCLOAK_URL = "http://localhost:8080"
TOKEN_URL = f"{KEYCLOAK_URL}/realms/mcp/protocol/openid-connect/token"

USERS = ["mara", "felix", "diana", "sam"]
ALL_USERS = USERS + ["anonymous"]

ALL_TOOLS = sorted([
    "query_public_data", "query_customer_data", "export_csv",
    "list_data_exports", "run_model", "manage_pipelines", "purge_dataset",
])
ALL_RESOURCES = sorted([
    "data://public/summary", "data://customers/segments",
    "data://models/catalog", "data://audit/log",
])

TOOL_CALLS = [
    ("query_public_data", {"dataset": "web_traffic"}),
    ("query_customer_data", {"segment": "high_value", "limit": 100}),
    ("export_csv", {"query_ref": "Q-001"}),
    ("list_data_exports", {}),
    ("run_model", {"model_id": "churn-predictor-v3", "dataset": "customers"}),
    ("manage_pipelines", {"operation": "list"}),
    ("purge_dataset", {"dataset_id": "legacy-2023", "reason": "GDPR test"}),
]

RESOURCE_READS = [
    ("data://public/summary", "resource_public_summary"),
    ("data://customers/segments", "resource_customers_segments"),
    ("data://models/catalog", "resource_models_catalog"),
    ("data://audit/log", "resource_audit_log"),
    ("data://models/churn-predictor-v3", "resource_model_detail"),
    ("data://customers/high_value/names", "resource_customer_names"),
]

PROMPT_GETS = [
    ("analyze_trends", {"dataset": "web_traffic"}),
    ("generate_report", {"report_type": "sales_summary"}),
    ("compliance_review", {}),
]


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def info(msg):
    print(f"\033[1;34m[INFO]\033[0m {msg}")


def ok(msg):
    print(f"\033[1;32m[ OK ]\033[0m {msg}")


def warn(msg):
    print(f"\033[1;33m[WARN]\033[0m {msg}")


def fail(msg):
    print(f"\033[1;31m[FAIL]\033[0m {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

server_proc: subprocess.Popen | None = None
tokens: dict[str, str] = {}
sessions: dict[str, str] = {}
responses: dict[str, dict[str, dict]] = {}


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def save_container_logs():
    """Dump docker container logs to LOG_DIR for post-mortem analysis."""
    for service in ("sapl-node", "keycloak"):
        result = subprocess.run(
            ["docker", "compose", "logs", "--no-color", service],
            cwd=MCP_DIR, capture_output=True, text=True,
        )
        if result.stdout:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            (LOG_DIR / f"{service}.log").write_text(result.stdout)


def cleanup():
    info("Shutting down...")
    save_container_logs()
    if server_proc and server_proc.poll() is None:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()
    subprocess.run(["docker", "compose", "down"], cwd=MCP_DIR, capture_output=True)
    info("Done.")


atexit.register(cleanup)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def wait_for(url: str, timeout: int, label: str, *, expect_200: bool = False):
    info(f"Waiting for {label}...")
    for elapsed in range(timeout):
        try:
            r = httpx.get(url, timeout=2)
            if expect_200 and r.status_code != 200:
                raise httpx.ConnectError("not 200 yet")
            ok(f"{label} ready ({elapsed}s)")
            return
        except httpx.HTTPError:
            time.sleep(1)
    fail(f"{label} not ready after {timeout}s")


def get_token(user: str) -> str | None:
    try:
        r = httpx.post(TOKEN_URL, data={
            "client_id": "mcp-server",
            "grant_type": "password",
            "username": user,
            "password": user,
        }, timeout=5)
        r.raise_for_status()
        return r.json().get("access_token") or None
    except Exception:
        return None


def parse_sse_body(text: str) -> str:
    """Extract the last ``data:`` line from an SSE response."""
    for line in reversed(text.splitlines()):
        if line.startswith("data: "):
            return line[6:]
    return text


def mcp_post(token: str | None, body: dict, user: str) -> dict:
    """POST a JSON-RPC message. Returns ``{"http_code": int, "body": ...}``."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if user in sessions:
        headers["mcp-session-id"] = sessions[user]

    try:
        r = httpx.post(MCP_ENDPOINT, json=body, headers=headers, timeout=10)
    except (httpx.ConnectError, httpx.TimeoutException):
        return {"http_code": 0, "body": None}

    sid = r.headers.get("mcp-session-id")
    if sid:
        sessions[user] = sid

    ct = r.headers.get("content-type", "")
    raw = parse_sse_body(r.text) if "text/event-stream" in ct else r.text

    try:
        parsed = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        parsed = None

    return {"http_code": r.status_code, "body": parsed}


def mcp_init(token: str, user: str) -> bool:
    resp = mcp_post(token, {
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "sapl-demo", "version": "1.0"},
        },
    }, user)
    if resp["http_code"] != 200:
        warn(f"Initialize failed for {user} (HTTP {resp['http_code']})")
        return False
    mcp_post(token, {"jsonrpc": "2.0", "method": "notifications/initialized"}, user)
    return True


def mcp_call(
    token: str | None, user: str, method: str, params: dict,
    label: str, rpc_id: int,
):
    resp = mcp_post(token, {
        "jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params,
    }, user)

    responses.setdefault(user, {})[label] = resp

    log_dir = LOG_DIR / user
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{label}.json").write_text(json.dumps(resp, indent=2))


def run_operations(user: str, token: str | None):
    info(f"--- {user} ---")
    rpc_id = 1

    if token:
        if not mcp_init(token, user):
            warn(f"Skipping {user} (init failed)")
            return
        ok(f"{user} session initialized")

    for method, params, label in [
        ("tools/list", {}, "tools_list"),
        ("resources/list", {}, "resources_list"),
        ("prompts/list", {}, "prompts_list"),
    ]:
        mcp_call(token, user, method, params, label, rpc_id)
        rpc_id += 1

    for name, args in TOOL_CALLS:
        mcp_call(token, user, "tools/call",
                 {"name": name, "arguments": args}, f"tool_{name}", rpc_id)
        rpc_id += 1

    for uri, label in RESOURCE_READS:
        mcp_call(token, user, "resources/read", {"uri": uri}, label, rpc_id)
        rpc_id += 1

    for name, args in PROMPT_GETS:
        mcp_call(token, user, "prompts/get",
                 {"name": name, "arguments": args}, f"prompt_{name}", rpc_id)
        rpc_id += 1

    ok(f"{user} complete ({rpc_id - 1} operations)")


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

def get_response(user: str, op: str) -> dict:
    return responses.get(user, {}).get(op, {"http_code": 0, "body": None})


def get_decision(resp: dict) -> str:
    http = resp["http_code"]
    body = resp["body"]

    if http != 200:
        return f"REJECT (HTTP {http})"
    if body is None:
        return "UNKNOWN"

    if "error" in body:
        msg = body["error"].get("message", "unknown")[:60]
        return f"DENY ({msg})"

    result = body.get("result")
    if isinstance(result, dict) and result.get("isError"):
        content = result.get("content", [])
        text = content[0].get("text", "denied")[:60] if content else "denied"
        return f"DENY ({text})"

    if result is not None:
        return "PERMIT"

    return "UNKNOWN"


def get_details(resp: dict, decision: str) -> str:
    if decision != "PERMIT":
        return "-"
    content = (resp.get("body") or {}).get("result", {}).get("content", [])
    if not content:
        return "OK"
    text = content[0].get("text", "")
    if not text:
        return "OK"
    try:
        return ", ".join(list(json.loads(text).keys())[:3])
    except (json.JSONDecodeError, AttributeError):
        return text[:60]


def get_names(resp: dict, field: str, subfield: str) -> list[str]:
    items = (resp.get("body") or {}).get("result", {}).get(field, [])
    return sorted(item.get(subfield, "") for item in items if isinstance(item, dict))


def generate_report():
    lines: list[str] = []
    w = lines.append

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    w(f"# SAPL MCP Demo Report -- {ts}")
    w("")

    # -- Listings --
    w("## Listings")
    w("")

    w("### tools/list")
    w("| User | Visible Tools | Hidden (stealth) |")
    w("|------|---------------|------------------|")
    for user in ALL_USERS:
        resp = get_response(user, "tools_list")
        if resp["http_code"] != 200:
            w(f"| {user} | *(HTTP {resp['http_code']})* | - |")
        else:
            visible = get_names(resp, "tools", "name")
            hidden = sorted(set(ALL_TOOLS) - set(visible))
            w(f"| {user} | {', '.join(visible) or '-'} | {', '.join(hidden) or '-'} |")
    w("")

    w("### resources/list")
    w("| User | Visible Resources | Hidden (stealth) |")
    w("|------|-------------------|------------------|")
    for user in ALL_USERS:
        resp = get_response(user, "resources_list")
        if resp["http_code"] != 200:
            w(f"| {user} | *(HTTP {resp['http_code']})* | - |")
        else:
            visible = get_names(resp, "resources", "uri")
            hidden = sorted(set(ALL_RESOURCES) - set(visible))
            w(f"| {user} | {', '.join(visible) or '-'} | {', '.join(hidden) or '-'} |")
    w("")

    w("### prompts/list")
    w("| User | Visible Prompts |")
    w("|------|-----------------|")
    for user in ALL_USERS:
        resp = get_response(user, "prompts_list")
        if resp["http_code"] != 200:
            w(f"| {user} | *(HTTP {resp['http_code']})* |")
        else:
            visible = get_names(resp, "prompts", "name")
            w(f"| {user} | {', '.join(visible) or '-'} |")
    w("")

    # -- Tool Calls --
    w("## Tool Calls")
    w("")
    for name, _ in TOOL_CALLS:
        w(f"### {name}")
        w("| User | Decision | Details |")
        w("|------|----------|---------|")
        for user in ALL_USERS:
            resp = get_response(user, f"tool_{name}")
            decision = get_decision(resp)
            details = get_details(resp, decision)
            w(f"| {user} | {decision} | {details} |")
        w("")

    # -- Resource Reads --
    w("## Resource Reads")
    w("")
    for uri, label in RESOURCE_READS:
        w(f"### {uri}")
        w("| User | Decision |")
        w("|------|----------|")
        for user in ALL_USERS:
            resp = get_response(user, label)
            decision = get_decision(resp)
            w(f"| {user} | {decision} |")
        w("")

    # -- Prompt Gets --
    w("## Prompt Gets")
    w("")
    for name, _ in PROMPT_GETS:
        w(f"### {name}")
        w("| User | Decision |")
        w("|------|----------|")
        for user in ALL_USERS:
            resp = get_response(user, f"prompt_{name}")
            decision = get_decision(resp)
            w(f"| {user} | {decision} |")
        w("")

    REPORT.write_text("\n".join(lines))


# =====================================================================
# Main
# =====================================================================

def kill_stale_port(port: int):
    result = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if f":{port} " in line:
            m = re.search(r"pid=(\d+)", line)
            if m:
                pid = int(m.group(1))
                warn(f"Killing stale process on port {port} (pid={pid})")
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)


def main():
    global server_proc

    # Phase 1: Cleanup
    info("Phase 1: Cleanup")
    subprocess.run(["docker", "compose", "down", "-v"], cwd=MCP_DIR, capture_output=True)
    if LOG_DIR.exists():
        shutil.rmtree(LOG_DIR)
    LOG_DIR.mkdir(parents=True)

    # Phase 2: Start infrastructure
    info("Phase 2: Starting infrastructure")
    subprocess.run(["docker", "compose", "up", "-d"], cwd=MCP_DIR, check=True)

    # Phase 3: Wait for services
    info("Phase 3: Waiting for services")
    wait_for(f"{KEYCLOAK_URL}/realms/mcp", 60, "Keycloak", expect_200=True)
    wait_for("http://localhost:8443", 30, "SAPL PDP")

    # Phase 4: Start analytics server
    info("Phase 4: Starting analytics server")
    kill_stale_port(8001)
    server_log = LOG_DIR / "server.log"
    with server_log.open("w") as log_fh:
        server_proc = subprocess.Popen(
            [str(VENV_PYTHON), "middleware_server.py"],
            cwd=SCRIPT_DIR, stdout=log_fh, stderr=subprocess.STDOUT,
        )
    wait_for(MCP_ENDPOINT, 15, "MCP server")
    if server_proc.poll() is not None:
        fail(f"Analytics server exited (see {server_log})")

    # Phase 5: Acquire tokens
    info("Phase 5: Acquiring tokens")
    for user in USERS:
        token = get_token(user)
        if not token:
            warn(f"Failed to get token for {user} -- skipping")
            continue
        tokens[user] = token
        ok(f"Token acquired for {user}")

    # Phase 6: Exercise endpoints
    info("Phase 6: Exercising endpoints")
    for user in USERS:
        if user not in tokens:
            continue
        run_operations(user, tokens[user])
    run_operations("anonymous", None)

    # Phase 7: Generate report
    info("Phase 7: Generating report")
    generate_report()
    ok(f"Report: {REPORT}")
    ok(f"Logs:   {LOG_DIR}/")

    info("Phase 8: Teardown (automatic via atexit)")


if __name__ == "__main__":
    main()
