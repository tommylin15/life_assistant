import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.google_integration import GoogleConnection, GoogleOAuthState
from app.services.google_identity import verify_google_id_token

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
IDENTITY_SCOPES = ("openid", "email", "profile")
SERVICE_SCOPES = {
    "gmail": ("https://www.googleapis.com/auth/gmail.readonly",),
    "calendar": ("https://www.googleapis.com/auth/calendar.events",),
    "drive": ("https://www.googleapis.com/auth/drive.file",),
}
TOKEN_KEY_CONTEXT = b"life-assistant-google-token-v1\x00"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_services(raw: str | None) -> tuple[str, ...]:
    values = [item.strip().lower() for item in (raw or "").split(",") if item.strip()]
    if not values:
        values = ["gmail", "calendar", "drive"]
    unknown = sorted(set(values) - set(SERVICE_SCOPES))
    if unknown:
        raise HTTPException(400, f"Unsupported Google service: {unknown[0]}")
    return tuple(dict.fromkeys(values))


def scopes_for_services(services: tuple[str, ...]) -> tuple[str, ...]:
    scopes = list(IDENTITY_SCOPES)
    for service in services:
        scopes.extend(SERVICE_SCOPES[service])
    return tuple(dict.fromkeys(scopes))


def granted_services(scopes: str) -> list[str]:
    granted = set(scopes.split())
    return [
        service
        for service, required in SERVICE_SCOPES.items()
        if set(required).issubset(granted)
    ]


def _key_candidates() -> list[bytes]:
    values: list[str] = []
    dedicated = os.environ.get("GOOGLE_TOKEN_ENCRYPTION_KEY", "").strip()
    if dedicated:
        values.append(dedicated)
    if settings.google_client_secret:
        values.append(settings.google_client_secret)
    candidates: list[bytes] = []
    for value in values:
        digest = hashlib.sha256(TOKEN_KEY_CONTEXT + value.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
        if key not in candidates:
            candidates.append(key)
    return candidates


def token_storage_ready() -> bool:
    return bool(_key_candidates())


def token_key_source() -> str:
    if os.environ.get("GOOGLE_TOKEN_ENCRYPTION_KEY", "").strip():
        return "dedicated"
    if settings.google_client_secret:
        return "oauth_client_secret_fallback"
    return "missing"


def encrypt_token(token: str) -> str:
    candidates = _key_candidates()
    if not candidates:
        raise HTTPException(503, "Google token storage is not configured")
    return Fernet(candidates[0]).encrypt(token.encode("utf-8")).decode("ascii")


def decrypt_token(ciphertext: str | None) -> str | None:
    if not ciphertext:
        return None
    for key in _key_candidates():
        try:
            return Fernet(key).decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except InvalidToken:
            continue
    raise HTTPException(503, "Stored Google authorization cannot be decrypted")


def _state_hash(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def build_authorization_url(state: str, services: tuple[str, ...]) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes_for_services(services)),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def create_authorization_state(
    db: AsyncSession,
    user: dict,
    services: tuple[str, ...],
) -> str:
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(503, "Google OAuth is not configured")
    if not token_storage_ready():
        raise HTTPException(503, "Google token storage is not configured")

    now = _now()
    await db.execute(delete(GoogleOAuthState).where(GoogleOAuthState.expires_at <= now))
    state = secrets.token_urlsafe(32)
    db.add(
        GoogleOAuthState(
            state_hash=_state_hash(state),
            user_sub=user["sub"],
            email=user["email"],
            services=",".join(services),
            expires_at=now + timedelta(minutes=10),
        )
    )
    await db.commit()
    return state


def _machine_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return "unknown_error"
    if not isinstance(payload, dict):
        return "unknown_error"
    value = str(payload.get("error", "")).strip()
    if not value or len(value) > 80 or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for ch in value):
        return "unknown_error"
    return value


async def _exchange_code(code: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
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
        raise HTTPException(503, "Google token exchange unavailable") from exc
    if response.status_code != 200:
        raise HTTPException(400, f"Google token exchange failed: {_machine_error(response)}")
    payload = response.json()
    if not payload.get("access_token") or not payload.get("id_token"):
        raise HTTPException(400, "Google token exchange returned an incomplete response")
    return payload


async def complete_authorization(
    db: AsyncSession,
    state: str,
    code: str,
    current_user: dict,
) -> tuple[str, ...]:
    state_row = await db.get(GoogleOAuthState, _state_hash(state))
    if not state_row or state_row.expires_at <= _now():
        raise HTTPException(400, "Invalid OAuth state")
    if state_row.user_sub != current_user["sub"] or state_row.email != current_user["email"]:
        raise HTTPException(400, "Invalid OAuth state")

    payload = await _exchange_code(code)
    claims = await verify_google_id_token(str(payload["id_token"]))
    if claims["sub"] != current_user["sub"] or claims["email"] != current_user["email"]:
        raise HTTPException(403, "Google authorization account does not match signed-in account")

    requested_services = normalize_services(state_row.services)
    existing = await db.get(GoogleConnection, current_user["sub"])
    granted = set(existing.scopes.split()) if existing else set()
    granted.update(scopes_for_services(requested_services))
    granted.update(str(payload.get("scope", "")).split())

    if existing is None:
        existing = GoogleConnection(
            user_sub=current_user["sub"],
            email=current_user["email"],
            scopes="",
        )
        db.add(existing)

    existing.email = current_user["email"]
    existing.encrypted_access_token = encrypt_token(str(payload["access_token"]))
    refresh_token = str(payload.get("refresh_token") or "")
    if refresh_token:
        existing.encrypted_refresh_token = encrypt_token(refresh_token)
    existing.scopes = " ".join(sorted(granted))
    try:
        expires_in = max(1, int(payload.get("expires_in", 3600)))
    except (TypeError, ValueError):
        expires_in = 3600
    existing.access_token_expires_at = _now() + timedelta(seconds=expires_in)

    await db.delete(state_row)
    await db.commit()
    return requested_services


async def get_access_token(
    db: AsyncSession,
    user_sub: str,
    required_scope: str,
    *,
    force_refresh: bool = False,
) -> str:
    connection = await db.get(GoogleConnection, user_sub)
    if connection is None:
        raise HTTPException(409, "Google integration is not connected")
    if required_scope not in set(connection.scopes.split()):
        raise HTTPException(403, "Google authorization does not include the required scope")

    now = _now()
    expires_at = connection.access_token_expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if (
        not force_refresh
        and connection.encrypted_access_token
        and expires_at is not None
        and expires_at > now + timedelta(seconds=60)
    ):
        token = decrypt_token(connection.encrypted_access_token)
        if token:
            return token

    refresh_token = decrypt_token(connection.encrypted_refresh_token)
    if not refresh_token:
        raise HTTPException(409, "Google reauthorization is required")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Google token refresh unavailable") from exc
    if response.status_code != 200:
        code = _machine_error(response)
        if code == "invalid_grant":
            raise HTTPException(409, "Google reauthorization is required")
        raise HTTPException(502, f"Google token refresh failed: {code}")

    payload = response.json()
    access_token = str(payload.get("access_token") or "")
    if not access_token:
        raise HTTPException(502, "Google token refresh returned an incomplete response")
    connection.encrypted_access_token = encrypt_token(access_token)
    try:
        expires_in = max(1, int(payload.get("expires_in", 3600)))
    except (TypeError, ValueError):
        expires_in = 3600
    connection.access_token_expires_at = now + timedelta(seconds=expires_in)
    if payload.get("scope"):
        connection.scopes = " ".join(sorted(set(connection.scopes.split()) | set(str(payload["scope"]).split())))
    await db.commit()
    return access_token
