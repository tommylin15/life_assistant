import hashlib
import logging
import os
import re
import secrets
import time
from urllib.parse import urlencode, urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.services.google_identity import verify_google_id_token
from app.services.google_oauth import IDENTITY_SCOPES, complete_authorization
from app.services.execution_log import start_execution, finish_execution

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
STAGING_HOST = "life-assistant-v3-stage-tl15.web.app"
STAGING_REDIRECT_URI = f"https://{STAGING_HOST}/auth/callback"

# Approved staging tester, fingerprinted to avoid publishing the email address.
_STAGING_TESTER_EMAIL_DIGESTS = frozenset({
    "4bf1494cf0fb01b437c3b8cdb5b510e6ea5fd7558fb10a08ac290f6b11826d08",
})


def _fixed_staging_origin(request: Request) -> bool:
    """Distinguish the approved Staging Hosting rewrite from production.

    Staging Firebase Hosting uses run.pinTag=true. Its verified Cloud Run Host
    is v3-<release SHA 10>---life-assistant-api-*.a.run.app, not the ordinary
    life-assistant-api-*.run.app service host. The tag routes to a 0%-traffic
    staging candidate revision; production Hosting routes to the untagged host.
    Firebase may omit the original X-Forwarded-Host.
    """
    host = request.headers.get("host", "").split(":", 1)[0].lower()
    if host == STAGING_HOST:
        return True

    tagged_candidate = re.fullmatch(
        r"v3-[0-9a-f]{10}---life-assistant-api-[a-z0-9-]+\.a\.run\.app",
        host,
    ) is not None
    ordinary_service = (
        host.endswith(".run.app")
        and (host.startswith("life-assistant-api-")
             or host.startswith("life-assistant-api."))
    )
    if not tagged_candidate and not ordinary_service:
        return False

    proto = request.headers.get("x-forwarded-proto", "").lower().split(",")[-1].strip()
    if proto and proto != "https":
        return False

    forwarded = request.headers.get("x-forwarded-host", "").strip().lower()
    allowed_forwarded = (STAGING_HOST, f"https://{STAGING_HOST}")
    if forwarded in allowed_forwarded:
        return True
    if forwarded and (".web.app" in forwarded or ".firebaseapp.com" in forwarded):
        return False

    if tagged_candidate:
        # Tag + named service identify the Staging-pinned revision even when
        # Firebase does not send a Referer/Origin (or forwarded Host).
        # A staging session cookie is still mandatory in current_user().
        return not forwarded

    # Backward compatibility for Firebase versions that proxy using the
    # ordinary service Host. Never let an explicit production origin through.
    fetch_site = request.headers.get("sec-fetch-site", "").strip().lower()
    if fetch_site not in ("", "same-origin", "same-site"):
        return False
    browser_origin = request.headers.get("origin") or request.headers.get("referer", "")
    try:
        parsed = urlsplit(browser_origin)
        return parsed.scheme == "https" and parsed.netloc.lower() == STAGING_HOST
    except ValueError:
        return False


def is_staging_tester(user: dict) -> bool:
    """Secondary user is never a privileged Owner."""
    owner = os.environ.get("ALLOWED_GOOGLE_EMAIL", "").strip().casefold()
    email = str(user.get("email", "")).strip().casefold()
    return bool(owner and email and email != owner
                and hashlib.sha256(email.encode("utf-8")).hexdigest()
                in _STAGING_TESTER_EMAIL_DIGESTS)


def _enforce_account_access(user: dict, *, staging: bool) -> None:
    """Grant signed-in access, never Owner authorization, to one stage tester."""
    owner = os.environ.get("ALLOWED_GOOGLE_EMAIL", "").strip().casefold()
    email = str(user.get("email", "")).strip().casefold()
    if not owner or email == owner:  # Preserve existing local-development behavior.
        return
    if staging and is_staging_tester(user):
        return
    raise _http_error(403, "Account is not allowed")


def _enforce_staging_tester_route(request: Request, user: dict) -> None:
    """Fail closed until non-tenant-scoped legacy resources have owner columns.

    Prior schema predates multi-user isolation for notes, habits, projects and
    shopping. Explicit safe routes may be tested; unaudited endpoints must
    not expose existing Owner rows to the secondary account.
    """
    if not is_staging_tester(user):
        return
    path = request.url.path.rstrip("/")
    safe_exact = {
        "/auth/me", "/auth/callback",
        "/api/v1/ui/features", "/api/v1/me/ui-preferences",
        "/api/v1/integrations/google/status",
        "/api/v1/integrations/google/authorize",
        "/api/v1/integrations/google/capabilities",
    }
    safe_prefixes = (
        "/api/v1/tasks/",
        "/api/v1/integrations/google/calendar",
        "/api/v1/integrations/google/gmail",
    )
    if (path in safe_exact or path == "/api/v1/tasks"
            or any(path.startswith(prefix) for prefix in safe_prefixes)):
        return
    raise _http_error(403, "Feature is unavailable for staging test account")



def oauth_redirect_for_request(request: Request) -> str:
    """Only the exact fixed staging origin gets staging OAuth.

    Never derive a redirect from an arbitrary forwarded host: an attacker may
    supply X-Forwarded-Host through an unauthenticated Cloud Run request.
    """
    # OAuth flow provenance survives Firebase's opaque proxy headers. Only a
    # successfully verified stage session or a stage-login state may select the
    # fixed, allowlisted staging callback; never use an arbitrary URL supplied
    # by a request parameter.
    session = request.cookies.get(SESSION_COOKIE, "")
    if session.startswith(("oauth:staging:", "id:staging:")):
        return STAGING_REDIRECT_URI
    hostname = request.headers.get("host", "").split(":", 1)[0].lower()
    forwarded = request.headers.get("x-forwarded-host", "").strip().lower()
    # Firebase Hosting typically forwards to a Cloud Run *.run.app Host, while
    # retaining the fixed public domain in X-Forwarded-Host. Trust this header
    # only for a known Cloud Run service hostname and exact staging allowlist.
    cloud_run_proxy = (
        hostname.endswith(".run.app")
        and (hostname.startswith("life-assistant-api-")
             or hostname.startswith("life-assistant-api."))
        and request.headers.get("x-forwarded-proto", "").lower() == "https"
    )
    if hostname == STAGING_HOST or (cloud_run_proxy and forwarded in (STAGING_HOST, f"https://{STAGING_HOST}")):
        return STAGING_REDIRECT_URI
    return settings.google_redirect_uri


def frontend_for_request(request: Request) -> str:
    if oauth_redirect_for_request(request) == STAGING_REDIRECT_URI:
        return f"https://{STAGING_HOST}"
    return settings.frontend_url.rstrip("/")

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


async def _audit_staging_e2e(
    db: AsyncSession, request: Request, user: dict, action_type: str,
) -> None:
    """Proof is written only after Google's verified owner authentication.

    The paired callback + subsequent session request are required by the
    staging acceptance job. No OAuth code/token/cookie or email is logged.
    """
    allowed = os.environ.get("ALLOWED_GOOGLE_EMAIL", "").strip().lower()
    revision = os.environ.get("K_REVISION", "").strip()
    if not (
        allowed and str(user.get("email", "")).strip().lower() == allowed
        and revision.startswith("life-assistant-api-")
        and (
            request.cookies.get(SESSION_COOKIE, "").startswith(
                ("oauth:staging:", "id:staging:")
            )
            or oauth_redirect_for_request(request) == STAGING_REDIRECT_URI
        )
    ):
        return
    log = await start_execution(
        db, user_sub=user["sub"], action_type=action_type,
        entity_type="cloud_run_revision", entity_id=revision,
        provider="google", summary="fixed_staging_google_oauth_acceptance",
    )
    await finish_execution(db, log)


async def current_user(request: Request) -> dict:
    session = request.cookies.get(SESSION_COOKIE, "")
    if not session.startswith("id:"):
        raise _http_error(401, "Missing session")
    token = session.removeprefix("id:")
    if token.startswith("staging:"):
        token = token.removeprefix("staging:")
    user = await _verify_id_token(token)
    _enforce_account_access(user, staging=(
        session.startswith('id:staging:') and _fixed_staging_origin(request)
    ))
    _enforce_staging_tester_route(request, user)
    return user


@router.get("/login")
async def login(request: Request):
    return await _login(request, force_staging=False)


@router.get("/staging/login")
async def staging_login(request: Request):
    # The route is a fixed choice, not an attacker-provided redirect target.
    # A production-domain caller cannot receive the staging callback cookie.
    return await _login(request, force_staging=True)


async def _login(request: Request, *, force_staging: bool):
    if not settings.google_client_id:
        raise _http_error(503, "Google OAuth client ID is not configured")

    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": STAGING_REDIRECT_URI if force_staging else oauth_redirect_for_request(request),
        "response_type": "code",
        "scope": SCOPES,
        "prompt": "select_account",  # Account switching, no implicit reuse.
        "state": state,
    }
    response = RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")
    response.set_cookie(
        SESSION_COOKIE,
        f"oauth:staging:{state}" if force_staging else f"oauth:{state}",
        max_age=600,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return response


async def _complete_login(code: str, redirect_uri: str) -> tuple[str, dict]:
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
                    "redirect_uri": redirect_uri,
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
        is_staging = session.startswith("oauth:staging:")
        expected_state = session.removeprefix("oauth:staging:" if is_staging else "oauth:")
        if not expected_state or not secrets.compare_digest(state, expected_state):
            raise _http_error(400, "Invalid OAuth state")

        callback_uri = STAGING_REDIRECT_URI if is_staging else oauth_redirect_for_request(request)
        id_token, user = await _complete_login(code, callback_uri)
        _enforce_account_access(user, staging=is_staging)
        await _audit_staging_e2e(db, request, user, "staging_google_callback")
        max_age = max(1, min(3600, int(user["exp"]) - int(time.time())))
        frontend_url = frontend_for_request(request) + "/"
        response = RedirectResponse(frontend_url)
        response.set_cookie(
            SESSION_COOKIE,
            f"id:staging:{id_token}" if is_staging else f"id:{id_token}",
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
    services = await complete_authorization(db, state, code, user, oauth_redirect_for_request(request))
    query = urlencode({"google": "connected", "services": ",".join(services)})
    return RedirectResponse(f"{frontend_for_request(request)}/integrations?{query}")


@router.get("/me")
async def me(
    request: Request,
    staging_e2e: bool = False,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    # A verified fixed-staging login should produce its session-side OAuth
    # evidence on the ordinary /auth/me request, without a hidden query flag.
    # _audit_staging_e2e still checks the real Google owner + K_REVISION.
    if staging_e2e or request.cookies.get(SESSION_COOKIE, "").startswith("id:staging:"):
        await _audit_staging_e2e(db, request, user, "staging_google_session")
    return {
        "email": user["email"],
        "name": user["name"],
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "ok"}
