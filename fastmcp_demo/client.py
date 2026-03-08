"""MCP client that exercises both authorization approaches.

Usage:
    python client.py simpleauthz <user>    -- per-component auth= on port 8000
    python client.py saplmiddleware <user> -- SAPL middleware on port 8001
"""

import asyncio
import json
import sys

import httpx
from mcp import ClientSession, McpError
from mcp.client.streamable_http import streamable_http_client

KEYCLOAK_TOKEN_URL = "http://localhost:8080/realms/mcp/protocol/openid-connect/token"
KEYCLOAK_CLIENT_ID = "mcp-server"

SERVERS = {
    "simpleauthz": "http://localhost:8000/mcp",
    "saplmiddleware": "http://localhost:8001/mcp",
}

LOG_RAW = False


def _format_error(e: Exception) -> str:
    if isinstance(e, McpError):
        code = e.error.code
        msg = e.error.message
        if code in (-32001, -32002) or "not found" in msg.lower():
            return f"NOT FOUND: {msg}"
        if code == -32000 or "access denied" in msg.lower():
            return f"DENIED: {msg}"
        return f"McpError [{code}]: {msg}"
    return f"{type(e).__name__}: {e}"


async def get_token(username: str) -> str:
    """Obtain a JWT from Keycloak using the resource-owner password grant."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            KEYCLOAK_TOKEN_URL,
            data={
                "grant_type": "password",
                "client_id": KEYCLOAK_CLIENT_ID,
                "username": username,
                "password": username,
            },
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def exercise_server(session: ClientSession, mode: str) -> None:
    """List all component types and exercise one of each."""
    await session.initialize()

    # List all component types
    tools_list = []
    resources_list = []
    templates_list = []
    prompts_list = []

    try:
        tools = await session.list_tools()
        tools_list = tools.tools
        print(f"\n{'='*60}")
        print(f"Tools ({len(tools_list)})")
        print(f"{'='*60}")
        for t in tools_list:
            if LOG_RAW:
                print(json.dumps(t.model_dump(exclude_none=True, mode="json"), indent=2))
            else:
                params = list(t.inputSchema.get("properties", {}).keys()) if t.inputSchema else []
                print(f"  {t.name}({', '.join(params)}): {t.description[:70]}...")
    except Exception as e:
        print(f"\nTools: {_format_error(e)}")

    try:
        resources = await session.list_resources()
        resources_list = resources.resources
        print(f"\n{'='*60}")
        print(f"Resources ({len(resources_list)})")
        print(f"{'='*60}")
        for r in resources_list:
            if LOG_RAW:
                print(json.dumps(r.model_dump(exclude_none=True, mode="json"), indent=2))
            else:
                print(f"  {r.uri}: {r.name}")
    except Exception as e:
        print(f"\nResources: {_format_error(e)}")

    try:
        templates = await session.list_resource_templates()
        templates_list = templates.resourceTemplates
        print(f"\n{'='*60}")
        print(f"Resource Templates ({len(templates_list)})")
        print(f"{'='*60}")
        for t in templates_list:
            if LOG_RAW:
                print(json.dumps(t.model_dump(exclude_none=True, mode="json"), indent=2))
            else:
                print(f"  {t.uriTemplate}: {t.name}")
    except Exception as e:
        print(f"\nResource Templates: {_format_error(e)}")

    try:
        prompts = await session.list_prompts()
        prompts_list = prompts.prompts
        print(f"\n{'='*60}")
        print(f"Prompts ({len(prompts_list)})")
        print(f"{'='*60}")
        for p in prompts_list:
            if LOG_RAW:
                print(json.dumps(p.model_dump(exclude_none=True, mode="json"), indent=2))
            else:
                args = [a.name for a in (p.arguments or [])]
                print(f"  {p.name}({', '.join(args)}): {p.description[:70]}...")
    except Exception as e:
        print(f"\nPrompts: {_format_error(e)}")

    # Exercise all components
    print(f"\n{'='*60}")
    print("Calling all tools")
    print(f"{'='*60}")

    if mode == "simpleauthz":
        tool_calls = [
            ("hello", {"name": "World"}),
            ("get_time", {}),
            ("read_config", {"key": "max_connections"}),
            ("write_config", {"key": "log_level", "value": "DEBUG"}),
        ]
    else:
        tool_calls = [
            ("query_public_data", {"dataset": "web_traffic"}),
            ("query_customer_data", {"segment": "high_value", "limit": 3}),
            ("export_csv", {"query_ref": "q-20250115-001"}),
            ("run_model", {"model_id": "churn-predictor-v3", "dataset": "high_value"}),
            ("manage_pipelines", {"operation": "list"}),
            ("purge_dataset", {"dataset_id": "legacy-2023", "reason": "GDPR erasure request #12345"}),
        ]

    for tool_name, args in tool_calls:
        print(f"\n-> {tool_name}({args})")
        try:
            result = await session.call_tool(tool_name, args)
            if result.isError:
                print(f"   DENIED: {result.content[0].text[:300]}")
            else:
                print(f"   {result.content[0].text[:300]}")
        except Exception as e:
            print(f"   {_format_error(e)}")

    print(f"\n{'='*60}")
    print("Reading all resources")
    print(f"{'='*60}")

    for r in resources_list:
        print(f"\n-> {r.uri}")
        try:
            result = await session.read_resource(r.uri)
            print(f"   {result.contents[0].text[:300]}")
        except Exception as e:
            print(f"   {_format_error(e)}")

    print(f"\n{'='*60}")
    print("Reading resource templates")
    print(f"{'='*60}")

    if mode == "simpleauthz":
        template_uris = [
            "config://features/dark_mode",
            "config://features/beta_api",
            "logs://access/2025-01-15",
        ]
    else:
        template_uris = [
            "data://models/churn-predictor-v3",
            "data://models/ltv-estimator-v2",
            "data://customers/high_value/emails",
            "data://customers/high_value/demographics",
        ]

    for uri in template_uris:
        print(f"\n-> {uri}")
        try:
            result = await session.read_resource(uri)
            print(f"   {result.contents[0].text[:300]}")
        except Exception as e:
            print(f"   {_format_error(e)}")

    print(f"\n{'='*60}")
    print("Getting all prompts")
    print(f"{'='*60}")

    if mode == "simpleauthz":
        prompt_calls = [
            ("summarize_status", {}),
            ("admin_report", {"date": "2025-01-15"}),
        ]
    else:
        prompt_calls = [
            ("analyze_trends", {"dataset": "web_traffic"}),
            ("generate_report", {"report_type": "quarterly_review", "audience": "management"}),
            ("compliance_review", {"regulation": "GDPR", "review_period": "last_7d"}),
        ]

    for prompt_name, args in prompt_calls:
        print(f"\n-> {prompt_name}({args})")
        try:
            result = await session.get_prompt(prompt_name, args if args else None)
            print(f"   {result.messages[0].content.text[:300]}")
        except Exception as e:
            print(f"   {_format_error(e)}")


async def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python client.py <simpleauthz|saplmiddleware> <user>")
        sys.exit(1)

    mode = sys.argv[1]
    user = sys.argv[2]

    if mode not in SERVERS:
        print(f"Unknown mode '{mode}'. Use 'simpleauthz' or 'saplmiddleware'.")
        sys.exit(1)

    server_url = SERVERS[mode]
    print(f"Mode: {mode}")
    print(f"Server: {server_url}")

    token = await get_token(user)
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Authenticated as: {user}")

    async with httpx.AsyncClient(headers=headers) as http_client:
        async with streamable_http_client(server_url, http_client=http_client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await exercise_server(session, mode)


if __name__ == "__main__":
    asyncio.run(main())
