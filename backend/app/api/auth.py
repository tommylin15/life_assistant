import os
import secrets
import time
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"

# Firebase Hosting only forwards the specially named __session cookie to
# rewritten Cloud Run backends. Prefix the value so an OAuth state cookie
# cannot be mistaken for an authenticated session.
SESSION_COOKIE = "__session"

SCOPES = " ".join([
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
])


def _http_error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


async def _verify_id_token(id_token: str) -> dict:
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

    email_verified = claims.get("email_verified")
    if str(email_verified).lower() != "true":
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


async def current_user(request: Request) -> dict:
    session = request.cookies.get(SESSION_COOKIE, "")
    if not session.startswith("id:"):
        raise _http_error(401, "Missing session")
    return await _verify_id_token(session.removeprefix("id:"))


@router.get("/login")
async def login():
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    response = RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")
    response.set_cookie(
        SESSION_COOKIE,
        f"oauth:{state}",
        max_age=600,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/callback")
async def callback(code: str, state: str, request: Request):
    expected_state = request.cookies.get(SESSION_COOKIE, "")
    expected_state = expected_state.removeprefix("oauth:") if expected_state.startswith("oauth:") else ""
    if not expected_state or not secrets.compare_digest(state, expected_state):
        raise _http_error(400, "Invalid OAuth state")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
    except httpx.HTTPError as exc:
        raise _http_error(503, "Google token exchange unavailable") from exc

    if token_resp.status_code != 200:
        raise _http_error(400, "Failed to exchange Google authorization code")

    id_token = str(token_resp.json().get("id_token", ""))
    user = await _verify_id_token(id_token)

    max_age = max(1, min(3600, int(user["exp"]) - int(time.time())))
    frontend_url = settings.frontend_url.rstrip("/") + "/"
    response = RedirectResponse(frontend_url)
    response.set_cookie(
        SESSION_COOKIE,
        f"id:{id_token}",
        max_age=max_age,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/me")
async def me(user: dict = Depends(current_user)):
    return {
        "email": user["email"],
        "name": user["name"],
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "ok"}
