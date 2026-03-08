"""MCP server demonstrating per-component auth=sapl() authorization.

Each tool, resource, resource template, and prompt is individually
protected with auth=sapl(). The PDP evaluates each component's
visibility and access independently, demonstrating selective listing
where different users see different subsets of the API surface.
"""

import logging
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic import Field
from sapl_base import PdpConfig
from handlers import AccessLoggingProvider
from sapl_fastmcp import configure_sapl, get_constraint_service, sapl

logging.basicConfig(level=logging.INFO)

configure_sapl(PdpConfig(
    base_url="http://localhost:8443",
    allow_insecure_connections=True,
))
get_constraint_service().register_runnable(AccessLoggingProvider())

auth = JWTVerifier(
    jwks_uri="http://localhost:8080/realms/mcp/protocol/openid-connect/certs",
    issuer="http://localhost:8080/realms/mcp",
)

mcp = FastMCP("sapl-demo", auth=auth)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    title="Hello Greeting",
    description="Greet someone by name. Returns a simple hello message.",
    tags={"public"},
    # sapl() with no arguments: defaults subject to token claims,
    # action to tool name ("hello"), resource to "mcp".
    auth=sapl(),
)
def hello(
    name: Annotated[str, Field(description="The name of the person to greet")],
) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"


@mcp.tool(
    title="Get Server Time",
    description="Returns the current server time in ISO format.",
    tags={"public"},
    # sapl() with explicit action: overrides the default (tool name)
    # so the policy sees action="read_status" instead of "get_time".
    auth=sapl(action="read_status"),
)
def get_time() -> str:
    """Return the current server time."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


@mcp.tool(
    title="Read Config",
    description="Read a server configuration value by key.",
    tags={"admin"},
    # sapl() with custom resource: policies can distinguish config reads
    # from other operations by matching on resource="server_config".
    auth=sapl(resource="server_config"),
)
def read_config(
    key: Annotated[str, Field(description="Configuration key to read, e.g. 'max_connections' or 'feature_flags'")],
) -> dict:
    """Read a configuration value."""
    config = {
        "max_connections": 100,
        "log_level": "INFO",
        "feature_flags": {"dark_mode": True, "beta_api": False},
    }
    return {"key": key, "value": config.get(key, "not_found")}


@mcp.tool(
    title="Write Config",
    description="Update a server configuration value. Requires admin access.",
    tags={"admin", "write"},
    # sapl() with custom subject extractor: passes only the username
    # instead of the full claims dict. Also passes the raw token as a
    # secret so policies can inspect custom claims if needed.
    auth=sapl(
        subject=lambda ctx: ctx.token.claims.get("preferred_username") if ctx.token else "anonymous",
        action="write_config",
        resource="server_config",
        secrets=lambda ctx: {"raw_token": ctx.token.token if ctx.token else None},
    ),
)
def write_config(
    key: Annotated[str, Field(description="Configuration key to update")],
    value: Annotated[str, Field(description="New value to set for the configuration key")],
) -> dict:
    """Update a configuration value."""
    return {"key": key, "value": value, "status": "updated"}


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource(
    "config://server/status",
    title="Server Status",
    description="Current server health and uptime information.",
    tags={"public"},
    mime_type="text/plain",
    # sapl() with defaults: action defaults to resource name
    # ("server_status"), resource to "mcp".
    auth=sapl(),
)
def server_status() -> str:
    """Server health status."""
    return (
        "Status: healthy\n"
        "Uptime: 14d 3h 22m\n"
        "Version: 1.2.0\n"
        "Connections: 42/100"
    )


@mcp.resource(
    "config://server/settings",
    title="Server Settings",
    description="Internal server configuration. Contains sensitive settings.",
    tags={"admin"},
    mime_type="text/plain",
    # sapl() with action override: policies match on action="read_settings"
    # and resource="server_config" to share policy with read_config tool.
    auth=sapl(action="read_settings", resource="server_config"),
)
def server_settings() -> str:
    """Internal server configuration."""
    return (
        "| Setting          | Value         |\n"
        "|------------------|---------------|\n"
        "| max_connections  | 100           |\n"
        "| log_level        | INFO          |\n"
        "| auth_provider    | keycloak      |\n"
        "| session_timeout  | 3600s         |"
    )


# ---------------------------------------------------------------------------
# Resource templates
# ---------------------------------------------------------------------------


@mcp.resource(
    "config://features/{feature_name}",
    title="Feature Flag",
    description="Check the status of a specific feature flag by name.",
    tags={"public"},
    mime_type="text/plain",
    # sapl() with defaults: good for simple read-only resources.
    auth=sapl(),
)
def feature_flag(
    feature_name: Annotated[str, Field(description="Name of the feature flag, e.g. 'dark_mode' or 'beta_api'")],
) -> str:
    """Status of a specific feature flag."""
    flags = {
        "dark_mode": "enabled",
        "beta_api": "disabled",
        "new_dashboard": "enabled (rollout: 50%)",
    }
    return f"{feature_name}: {flags.get(feature_name, 'unknown')}"


@mcp.resource(
    "logs://access/{date}",
    title="Access Log by Date",
    description="Access log entries for a specific date. Contains user activity data.",
    tags={"admin"},
    mime_type="text/plain",
    # sapl() with environment: passes additional context to the PDP.
    # Policies can use environment.component_type to apply rules
    # specifically to resource template access.
    auth=sapl(
        action="read_access_log",
        environment=lambda ctx: {"component_type": "resource_template"},
    ),
)
def access_log(
    date: Annotated[str, Field(description="Date to retrieve logs for, in YYYY-MM-DD format")],
) -> str:
    """Access log entries for a given date."""
    return (
        f"Access log for {date}:\n"
        "| Time     | User    | Action      | Status |\n"
        "|----------|---------|-------------|--------|\n"
        "| 09:14:02 | alice   | hello       | permit |\n"
        "| 09:15:30 | bob     | read_config | deny   |\n"
        "| 09:22:11 | alice   | write_config| permit |"
    )


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt(
    title="Summarize Status",
    description="Generate a summary of the current server status and health.",
    tags={"public"},
    # sapl() with defaults: action="summarize_status".
    auth=sapl(),
)
def summarize_status() -> str:
    """Summarize server status."""
    return (
        "Read the config://server/status resource and provide a brief "
        "summary of the server health. Highlight any concerns."
    )


@mcp.prompt(
    title="Admin Report",
    description="Generate an administrative report including settings and access logs.",
    tags={"admin"},
    # sapl() with custom subject and action: demonstrates that prompt
    # access can be governed by the same policy rules as tools.
    auth=sapl(
        subject=lambda ctx: {
            "username": ctx.token.claims.get("preferred_username") if ctx.token else "anonymous",
            "roles": ctx.token.claims.get("realm_access", {}).get("roles", []) if ctx.token else [],
        },
        action="generate_admin_report",
    ),
)
def admin_report(
    date: Annotated[str, Field(description="Date for the report in YYYY-MM-DD format, or 'today'")] = "today",
) -> str:
    """Generate an admin report."""
    return (
        f"Generate an administrative report for {date}.\n\n"
        "1. Read config://server/settings for current configuration.\n"
        "2. Read logs://access/{date} for recent access activity.\n"
        "3. Summarize any configuration changes or access anomalies."
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
