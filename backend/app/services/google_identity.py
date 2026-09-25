import os
import time

import httpx
from fastapi import HTTPException

from app.config import settings

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


def _http_error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


async def verify_google_id_token(id_token: str) -> dict:
    if not id_token:
        raise _http_error(401, "Missing session")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(GOOGLE_TOKENINFO_URL, params={"id_token": id_token})
    except httpx.HTTPError as exc:
        raise _http_error(503, "Authentication service unavailable") from exc

    if response.status_code != 200:
        raise _http_error(401, "Invalid session")

    claims = response.json()
    if claims.get("aud") != settings.google_client_id:
        raise _http_error(401, "Invalid token audience")
    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise _http_error(401, "Invalid token issuer")

    if str(claims.get("email_verified")).lower() != "true":
        raise _http_error(401, "Google email is not verified")

    try:
        expires_at = int(claims.get("exp", 0))
    except (TypeError, ValueError):
        expires_at = 0
    if expires_at <= int(time.time()):
        raise _http_error(401, "Session expired")

    email = str(claims.get("email", "")).strip().lower()
    if not email:
        raise _http_error(401, "Token does not contain an email")

    allowed_email = os.environ.get("ALLOWED_GOOGLE_EMAIL", "").strip().lower()
    if allowed_email and email != allowed_email:
        raise _http_error(403, "Account is not allowed")

    return {
        "sub": str(claims.get("sub", "")),
        "email": email,
        "name": str(claims.get("name") or email),
        "exp": expires_at,
    }
