"""Life -> private omniAgent Gateway -> Gemini Flash-Lite: explicit text-only path.

No Drive lookup, document enrichment, cache mutation, provider key or DB write.
Caller identity comes from the Cloud Run metadata server; owner identity comes
only from the already-verified Life session, never the submitted request.
"""
import re
import uuid

import httpx

from app.config import settings
from app.services.ai_enrichment_provider import codex_owner_uuid

PROJECT = "life-assistant"
MODEL = "gemini-3.5-flash-lite"
AUDIENCE = "https://omniagent-agent-gateway-2oo7qbkd5q-uc.a.run.app"
METADATA = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/"
MAX_PROMPT_BYTES = 8192
MAX_TEXT_CHARS = 32000
# Only the approved Gateway service, with an optional Cloud Run traffic tag.
_GATEWAY_URL = re.compile(
    r"^https://(?:[a-z][a-z0-9-]*---)?omniagent-agent-gateway-2oo7qbkd5q-uc[.]a[.]run[.]app$"
)


class GatewayTextError(Exception):
    def __init__(self, code: str, status_code: int = 502):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


async def _mint_identity(client: httpx.AsyncClient) -> str:
    """Direct metadata identity: no IAMCredentials impersonation or JSON keys."""
    expected = settings.codex_shared_caller_service_account.strip().lower()
    try:
        email = await client.get(METADATA + "email", headers={"Metadata-Flavor": "Google"})
        if email.status_code != 200 or email.text.strip().lower() != expected:
            raise GatewayTextError("service_identity_unavailable", 503)
        token = await client.get(
            METADATA + "identity",
            headers={"Metadata-Flavor": "Google"},
            params={"audience": AUDIENCE, "format": "full"},
        )
    except httpx.HTTPError as exc:
        raise GatewayTextError("service_identity_unavailable", 503) from exc
    if token.status_code != 200 or not token.text.strip():
        raise GatewayTextError("service_identity_unavailable", 503)
    return token.text.strip()


async def generate_text(prompt: str, *, user_sub: str) -> dict[str, str]:
    """One authenticated invocation, zero retries, no persistence or side effects."""
    if not settings.gemini_gateway_text_enabled:
        raise GatewayTextError("gemini_text_disabled", 503)
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
        raise GatewayTextError("invalid_prompt", 400)
    target = settings.gemini_gateway_url.rstrip("/")
    if not _GATEWAY_URL.fullmatch(target) or settings.codex_shared_caller_service_account != (
        "omniagent-codex-life-client@gen-lang-client-0593591102.iam.gserviceaccount.com"
    ):
        raise GatewayTextError("gateway_configuration_unavailable", 503)

    owner_id = codex_owner_uuid(user_sub)
    request_id = str(uuid.uuid4())
    body = {
        "project": PROJECT, "ownerId": owner_id, "requestId": request_id,
        "prompt": prompt, "model": MODEL,
    }

    try:
        async with httpx.AsyncClient(timeout=70.0) as client:
            id_token = await _mint_identity(client)
            response = await client.post(
                target + "/v1/gemini/execute",
                headers={"Authorization": "Bearer " + id_token, "Content-Type": "application/json"},
                json=body,
            )
    except httpx.TimeoutException as exc:
        # The provider might have run. Never transparently retry an uncertain request.
        raise GatewayTextError("gateway_timeout", 504) from exc
    except httpx.HTTPError as exc:
        raise GatewayTextError("gateway_unavailable", 502) from exc

    if response.status_code != 200:
        if response.status_code == 429:
            raise GatewayTextError("gateway_busy", 503)
        if response.status_code in (401, 403):
            raise GatewayTextError("gateway_identity_rejected", 502)
        raise GatewayTextError("gateway_execution_failed", 502)
    try:
        payload = response.json()
    except (TypeError, ValueError) as exc:
        raise GatewayTextError("gateway_invalid_response", 502) from exc
    if not isinstance(payload, dict):
        raise GatewayTextError("gateway_invalid_response", 502)
    result = payload.get("result")
    text = result.get("text") if isinstance(result, dict) else None
    if (
        payload.get("status") != "completed"
        or payload.get("project") != PROJECT
        or payload.get("ownerId") != owner_id
        or payload.get("requestId") != request_id
        or payload.get("model") != MODEL
        or not isinstance(text, str)
        or not text.strip()
        or len(text) > MAX_TEXT_CHARS
    ):
        raise GatewayTextError("gateway_invalid_response", 502)
    return {"status": "completed", "request_id": request_id, "model": MODEL, "text": text}
