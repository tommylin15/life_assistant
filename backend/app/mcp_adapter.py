"""Small remote MCP adapter; all curated business logic remains in REST.

This is hosted with the existing Life Cloud Run service and can be called from
ChatGPT web/mobile when the client supports the connected remote plugin.
Inbound key: LIFE_MCP_CLIENT_TOKEN. Outbound key: LIFE_CURATED_INGEST_TOKEN.
Neither is a tool argument nor committed to the plugin package.
"""
import os
from datetime import date
from typing import Any

import httpx
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from app.api.curated import CuratedBatchIn, CuratedItemIn

mcp = MCPServer("Life Curator")


async def _call_life_rest(
    method: str, path: str, *, payload: dict | None = None,
    params: dict | None = None,
) -> dict:
    """Loop back through the actual FastAPI REST contract, not the ORM."""
    writer = os.environ.get("LIFE_CURATED_INGEST_TOKEN", "")
    if len(writer) < 32:
        raise RuntimeError("Life curated REST writer is not configured")
    # Deferred import avoids a circular dependency during app startup.
    from app.main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://life.internal",
        timeout=20.0,
    ) as client:
        response = await client.request(
            method, path, json=payload, params=params,
            headers={"Authorization": f"Bearer {writer}"},
        )
    if response.status_code != 200:
        # Don't put request bodies, source URLs or credentials in error logs.
        raise RuntimeError(f"Life curated REST returned HTTP {response.status_code}")
    result: dict[str, Any] = response.json()
    return result


@mcp.tool()
async def curated_upsert(items: list[CuratedItemIn]) -> dict:
    """Write 1–40 independently sourced curated activities; retries upsert by URL and occurrence."""
    validated = CuratedBatchIn(items=items)
    return await _call_life_rest(
        "POST", "/api/v1/free-events/curated:batch",
        payload=validated.model_dump(mode="json", exclude_unset=True),
    )


@mcp.tool()
async def curated_list(
    min_importance: int = 1, limit: int = 20, offset: int = 0,
    city: str | None = None, category: str | None = None,
    starts_from: date | None = None,
) -> dict:
    """Read Life's persisted curated pool, optionally filtered by rating, area and dates."""
    params = {"min_importance": min_importance, "limit": limit, "offset": offset}
    if city is not None:
        params["city"] = city
    if category is not None:
        params["category"] = category
    if starts_from is not None:
        params["starts_from"] = starts_from.isoformat()
    return await _call_life_rest("GET", "/api/v1/free-events/curated:connector", params=params)


@mcp.tool()
async def curated_status() -> dict:
    """Read the number of persisted activities and their latest update time."""
    return await _call_life_rest("GET", "/api/v1/free-events/curated:connector/status")


# Fixed cloud hostnames and protected origins, not local-only MCP.
# The wildcard is needed because Firebase Hosting forwards to a Cloud Run
# instance hostname; separate bearer auth is mandatory on every MCP request.
security = TransportSecuritySettings(
    allowed_hosts=[
        "life-assistant-v3-stage-tl15.web.app",
        "gen-lang-client-0593591102.web.app",
        "*.run.app",
        "localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*", "testserver",
    ],
    allowed_origins=["https://chatgpt.com", "https://chat.openai.com"],
)
mounted_mcp_app = mcp.streamable_http_app(
    streamable_http_path="/", stateless_http=True, json_response=True,
    transport_security=security,
)
