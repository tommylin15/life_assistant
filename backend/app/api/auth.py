import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from jose import jwt

from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

SCOPES = " ".join([
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
])


@router.get("/login")
async def login():
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{query}")


@router.get("/callback")
async def callback(code: str):
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        })

    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange token")

    tokens = token_resp.json()

    # decode id_token to get user info (no signature verify needed here, Google already validated)
    id_token = tokens.get("id_token", "")
    user_info = jwt.get_unverified_claims(id_token) if id_token else {}

    # Redirect back to Flutter Web with token in query params
    frontend_url = settings.frontend_url
    email = user_info.get("email", "")
    name = user_info.get("name", "")
    access_token = tokens.get("access_token", "")
    return RedirectResponse(
        f"{frontend_url}/auth/callback?access_token={access_token}&email={email}&name={name}"
    )


@router.get("/me")
async def me():
    # placeholder — will require auth middleware later
    return {"status": "not implemented"}
