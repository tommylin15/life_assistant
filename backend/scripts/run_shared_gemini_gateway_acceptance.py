"""Bounded real signed Gateway call from a Life Cloud Run Job runtime.

Synthetic public prompt; no user context, DB writes, provider keys or logging
of the returned text. This is not an authenticated user/API round-trip.
"""
import asyncio
import sys

from app.config import settings
from app.services.shared_gemini_gateway import GatewayTextError, generate_text


async def main() -> int:
    if len(sys.argv) != 2:
        print("life_gateway_signed_smoke=FAIL reason=missing_candidate_url")
        return 2
    settings.gemini_gateway_text_enabled = True
    settings.gemini_gateway_url = sys.argv[1]
    try:
        answer = await generate_text(
            "Reply in one short sentence confirming Life Gateway text connectivity.",
            user_sub="life-gemini-ci-synthetic-no-user-data",
        )
    except GatewayTextError as exc:
        print("life_gateway_signed_smoke=FAIL reason=" + exc.code)
        return 1
    if answer.get("status") != "completed" or not answer.get("text", "").strip():
        print("life_gateway_signed_smoke=FAIL reason=empty_response")
        return 1
    print("life_gateway_signed_smoke=PASS model=flash-lite request_match=PASS text=NONEMPTY")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
