"""Small LINE transport and authentication boundary. No agent runtime."""
import base64
import hashlib
import hmac
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit

import httpx
from fastapi import HTTPException, Request

from app.models.line import LineBinding, LineSession


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def utcnow():
    return datetime.now(timezone.utc)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def configuration() -> dict:
    cfg = {key: os.environ.get("LIFE_LINE_" + key.upper(), "").strip()
           for key in ("enabled", "namespace", "origin", "liff_id", "login_channel_id",
                       "channel_secret", "access_token")}
    origin = urlsplit(cfg["origin"])
    if (cfg["enabled"] != "true" or not all(cfg.values())
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", cfg["namespace"])
            or origin.scheme != "https" or not origin.hostname
            or origin.username or origin.password or origin.query or origin.fragment
            or origin.path not in ("", "/")):
        raise HTTPException(503, "LINE integration is not configured")
    cfg["origin"] = cfg["origin"].rstrip("/")
    return cfg


def check_origin(request: Request, cfg: dict):
    # Fixed configured origin, never a user-controlled forwarded Host.
    if request.headers.get("origin", "") != cfg["origin"]:
        raise HTTPException(403, "Invalid LINE page origin")


def verify_signature(raw: bytes, signature: str, secret: str):
    expected = base64.b64encode(hmac.new(secret.encode(), raw, hashlib.sha256).digest()).decode()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(401, "Invalid LINE signature")


def liff_url(cfg: dict, **params) -> str:
    return "https://liff.line.me/" + cfg["liff_id"] + ("?" + urlencode(params) if params else "")


async def verify_id_token(token: str, cfg: dict) -> str:
    async with httpx.AsyncClient(timeout=8) as client:
        try:
            response = await client.post("https://api.line.me/oauth2/v2.1/verify", data={
                "id_token": token, "client_id": cfg["login_channel_id"]})
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError):
            raise HTTPException(401, "LINE identity could not be verified") from None
    if (data.get("aud") != cfg["login_channel_id"]
            or data.get("iss") != "https://access.line.me"
            or not isinstance(data.get("exp"), (int, float))
            or data["exp"] <= utcnow().timestamp()
            or not re.fullmatch(r"U[0-9a-f]{32}", str(data.get("sub", "")))):
        raise HTTPException(401, "Invalid LINE identity")
    return data["sub"]


async def reply_message(token: str, messages: list, cfg: dict):
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            response = await client.post("https://api.line.me/v2/bot/message/reply",
                headers={"Authorization": "Bearer " + cfg["access_token"]},
                json={"replyToken": token, "messages": messages})
            response.raise_for_status()
        except httpx.HTTPError:
            # No automatic Push fallback (cost/privacy). Draft remains accessible.
            raise HTTPException(503, "LINE reply unavailable; draft retained") from None


def permitted_line_path(path: str, method: str) -> bool:
    """A linked Owner never inherits admin/Drive/Gmail powers in LINE."""
    if path in ("/auth/me", "/auth/logout", "/api/v1/ui/features"):
        return True
    if path.startswith("/api/v1/line/"):
        return not path.startswith("/api/v1/line/link")
    if path.startswith(("/api/v1/tasks", "/api/v1/notes", "/api/v1/shopping-lists",
                        "/api/v1/shopping-items", "/api/v1/inbox/")):
        return True
    if path.startswith("/api/v1/integrations/google/calendar"):
        return True
    if path.startswith("/api/v1/free-events/curated"):
        return ":" not in path and not path.endswith("/status")
    return False


async def read_line_session(request: Request, db, cookie: str) -> dict:
    cfg = configuration()
    bearer = cookie.removeprefix("ln:")
    if not re.fullmatch(r"[A-Za-z0-9_-]{64}", bearer):
        raise HTTPException(401, "Invalid LINE session")
    session = await db.get(LineSession, digest(bearer))
    if session is None or aware(session.expires_at) <= utcnow():
        raise HTTPException(401, "LINE session expired")
    binding = await db.get(LineBinding, session.binding_id)
    if binding is None or not binding.active or binding.namespace != cfg["namespace"]:
        raise HTTPException(401, "LINE account is not linked")
    if not permitted_line_path(request.url.path, request.method):
        raise HTTPException(403, "Open Life with Google login for this operation")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        check_origin(request, cfg)
    user = {"sub": binding.user_sub, "email": binding.email, "name": binding.display_name,
            "line_binding_id": binding.id}
    from app.api.ui_policies import feature_gate
    await feature_gate("line")(user=user, db=db)
    return user
