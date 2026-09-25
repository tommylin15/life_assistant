import logging
import re
import secrets
import time
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.services.google_identity import verify_google_id_token
from app.services.google_oauth import IDENTITY_SCOPES, complete_authorization

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Firebase Hosting only forwards the specially named __session cookie to
# rewritten Cloud Run backends. Prefix the value so an OAuth state cookie
# cannot be mistaken for an authenticated session.
SESSION_COOKIE = "__session"
SCOPES = " ".join(IDENTITY_SCOPES)
_verify_id_token = verify_google_id_token


def _http_error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


def _google_error_code(response: httpx.Response) -> str:
    """Return only Google's machine-readable OAuth error code, never secrets."""
    try:
        payload = response.json()
    except ValueError:
        return "unknown_error"
    if not isinstance(payload, dict):
        return "unknown_error"
    error = str(payload.get("error", "")).strip()
    if not error or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", error):
        return "unknown_error"
    return error


async def current_user(request: Request) -> dict:
    session = request.cookies.get(SESSION_COOKIE, "")
    if not session.startswith("id:"):
        raise _http_error(401, "Missing session")
    return await _verify_id_token(session.removeprefix("id:"))


@router.get("/login")
async def login():
    if not settings.google_client_id:
        raise _http_error(503, "Google OAuth client ID is not configured")

    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
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


async def _complete_login(code: str) -> tuple[str, dict]:
    if not settings.google_client_secret:
        raise _http_error(503, "Google OAuth client secret is not configured")

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
        error_code = _google_error_code(token_resp)
        logger.warning(
            "Google OAuth token exchange failed: status=%s error=%s",
            token_resp.status_code,
            error_code,
        )
        raise _http_error(400, f"Google token exchange failed: {error_code}")

    id_token = str(token_resp.json().get("id_token", ""))
    user = await _verify_id_token(id_token)
    return id_token, user


@router.get("/callback")
async def callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    session = request.cookies.get(SESSION_COOKIE, "")
    if session.startswith("oauth:"):
        expected_state = session.removeprefix("oauth:")
        if not expected_state or not secrets.compare_digest(state, expected_state):
            raise _http_error(400, "Invalid OAuth state")

        id_token, user = await _complete_login(code)
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

    # Incremental Gmail/Calendar/Drive authorization keeps the authenticated
    # session cookie intact and stores its one-time state server-side.
    user = await current_user(request)
    services = await complete_authorization(db, state, code, user)
    query = urlencode({"google": "connected", "services": ",".join(services)})
    return RedirectResponse(f"{settings.frontend_url.rstrip('/')}/integrations?{query}")


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
