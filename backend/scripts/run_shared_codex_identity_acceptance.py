#!/usr/bin/env python3
"""Private shared Codex consumer identity and isolation runtime acceptance.

Only synthetic prompts. No real user/Drive data and no persistent DB writes.
Requires the real life_assistant Cloud Run Job's service identity, NOT CI identity.
"""
import asyncio
import json
import uuid

import httpx

from app.services.ai_enrichment_provider import (
    SharedCodexEnrichmentProvider,
    codex_owner_uuid,
)

AUDIENCE = "https://omniagent-shared-codex-2oo7qbkd5q-uc.a.run.app"
URL = AUDIENCE + "/v1/codex/execute"
TIMEOUT = httpx.Timeout(175.0, connect=10.0)


async def main() -> None:
    owner_id = codex_owner_uuid("synthetic-shared-codex-acceptance")
    request_id = str(uuid.uuid4())
    body = {
        "project": "life-assistant",
        "ownerId": owner_id,
        "requestId": request_id,
        "prompt": "Return one short plain-text response about a synthetic planning checklist only.",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Do not print tokens. These are actual GCP runtime mint/Invoke tests.
        signed_token = await SharedCodexEnrichmentProvider(owner_id=owner_id)._mint_google_id_token(client)

        anonymous = await client.post(URL, json=body)
        if anonymous.status_code not in (401, 403):
            raise AssertionError("shared_codex_anonymous_rejection_failed")
        print(f"shared_codex_anonymous=PASS status={anonymous.status_code}", flush=True)

        headers = {"Authorization": "Bearer " + signed_token}
        mismatch = await client.post(URL, json={**body, "project": "market-mart"}, headers=headers)
        if mismatch.status_code != 403:
            raise AssertionError("shared_codex_project_isolation_failed")
        print("shared_codex_project_isolation=PASS status=403", flush=True)

        real = await client.post(URL, json=body, headers=headers)
        if real.status_code != 200:
            print(f"shared_codex_real=FAIL request_id={request_id} http={real.status_code}", flush=True)
            raise AssertionError("shared_codex_real_inference_failed")
        envelope = real.json()
        trace = envelope.get("providerIds") if isinstance(envelope, dict) else None
        text = envelope.get("result", {}).get("text") if isinstance(envelope, dict) else None
        if (
            envelope.get("status") != "completed"
            or envelope.get("project") != "life-assistant"
            or envelope.get("ownerId") != owner_id
            or envelope.get("requestId") != request_id
            or not isinstance(text, str)
            or not text.strip()
            or not isinstance(trace, dict)
            or not all(isinstance(trace.get(key), str) and trace[key] for key in ("threadId","turnId"))
        ):
            raise AssertionError("shared_codex_response_contract_failed")
        print(f"shared_codex_real=PASS request_id={request_id} http=200 thread_and_turn=present", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
